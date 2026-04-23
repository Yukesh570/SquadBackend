import asyncio
import struct
import logging
import datetime
import time
import uuid
import aiohttp
from django.core.management.base import BaseCommand
from asgiref.sync import sync_to_async
from django.db.models import Q

# Replace this with your actual app import
from squadServices.models.clientModel.client import Client, PuskarClient

# --- Configuration ---
HOST = "0.0.0.0"
PORT = 2776
HOST1 = "0.0.0.0"
PORT1 = 2777

# --- SMPP Command IDs ---
CMD_BIND_TRANSCEIVER = 0x00000009
CMD_BIND_TRANSCEIVER_RESP = 0x80000009
CMD_SUBMIT_SM = 0x00000004
CMD_SUBMIT_SM_RESP = 0x80000004
CMD_DELIVER_SM = 0x00000005
CMD_ENQUIRE_LINK = 0x00000015
CMD_ENQUIRE_LINK_RESP = 0x80000015

# --- SMPP Status ---
ESME_ROK = 0x00000000

# Logging Setup
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Command(BaseCommand):
    help = "High-Performance SMPP Server with Async HTTP and Memory Management"

    # In-memory store for concatenated messages
    # Structure: { ref_num: { "total": int, "parts": { part_num: text }, "source": str, "dest": str, "timestamp": float } }
    message_store = {}

    # Expiration time for incomplete segmented messages (in seconds)
    MESSAGE_TIMEOUT = 300

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS(f"Starting SMPP Server..."))
        try:
            asyncio.run(self.run_server())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nServer stopped gracefully."))

    async def generate_message_id(self):
        return str(uuid.uuid4())

    async def run_server(self):
        # 1. Initialize a persistent HTTP connection pool (Limit concurrent connections to protect target API)
        connector = aiohttp.TCPConnector(limit=500)
        self.http_session = aiohttp.ClientSession(connector=connector)

        # 2. Start the background memory cleanup task
        cleanup_task = asyncio.create_task(self.cleanup_stale_messages())

        # 3. Start the SMPP Listeners
        server1 = await asyncio.start_server(self.handle_client, HOST, PORT)
        self.stdout.write(f"Server 1 listening on {HOST}:{PORT}")

        server2 = await asyncio.start_server(self.handle_client, HOST1, PORT1)
        self.stdout.write(f"Server 2 listening on {HOST1}:{PORT1}")

        try:
            async with server1, server2:
                await asyncio.gather(server1.serve_forever(), server2.serve_forever())
        finally:
            # 4. Graceful shutdown
            cleanup_task.cancel()
            await self.http_session.close()

    async def cleanup_stale_messages(self):
        """Background task to remove incomplete segmented messages to prevent memory leaks."""
        while True:
            await asyncio.sleep(60)  # Run every 60 seconds
            current_time = time.time()
            stale_refs = []

            for ref, data in self.message_store.items():
                if current_time - data["timestamp"] > self.MESSAGE_TIMEOUT:
                    stale_refs.append(ref)

            for ref in stale_refs:
                logger.warning(f"Dropping stale message segments for Ref: {ref}")
                del self.message_store[ref]

    async def process_and_receipt(
        self, writer, sms_info, msg_id_str, seq_num, clientdata, client_dlr_status
    ):
        """Runs the HTTP request and sends the DLR in the background."""
        response = await self.callApi(
            sms_info["text"],
            sms_info["dest"],
            clientdata,
            client_dlr_status,
        )
        # print(f"Webhook Response Status: {response.status_code}")

        if response.status_code == 406:
            logger.warning("SQUAD SERVER REJECTED MESSAGE: Subscription Expired")
            return  # Skip sending DLR

        # Send Success DLR
        await self.send_dlr(
            writer,
            sms_info,
            sms_info["text"],
            msg_id_str,
            seq_num + 1000,
            client_dlr_status,
        )

    @sync_to_async
    def authenticate_client(self, username, password):
        """Strictly handles authentication via Django ORM."""
        try:
            client = PuskarClient.objects.filter(
                (Q(DsmppUsername=username) | Q(FsmppUsername=username)),
                smppPassword=password,
                isDeleted=False,
            ).first()

            if not client:
                logger.warning(
                    f"Auth Failed: Invalid credentials or deleted account for '{username}'."
                )
                return None

            return client
        except Exception as e:
            logger.error(f"Auth Lookup Error for '{username}': {e}")
            return None

    async def callApi(self, sms_text, destination, source, client_dlr_status):
        """Sends the HTTP webhook using the persistent aiohttp session."""
        if client_dlr_status == "DELIVRD":
            api = "https://boss.arssapp.com/sms_test/api/sms/deliverAdd"
        else:
            api = "https://boss.arssapp.com/sms_test/api/sms/deliveryFailedAdd"

        payload = {
            "messageContent": sms_text,
            "toUser": destination,
            "userID": source.id,
        }

        try:
            async with self.http_session.post(api, json=payload) as res:
                await res.read()  # Read the response to free the connection back to the pool

                # Mock response object for compatibility with existing logic
                class DummyResponse:
                    status_code = res.status

                return DummyResponse()

        except Exception as e:
            logger.error(f"Webhook Delivery Failed: {e}")

            class DummyResponse:
                status_code = 500

            return DummyResponse()

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info("peername")
        # ADD THIS: Give this specific connection its own traffic light
        writer.write_lock = asyncio.Lock()
        server_info = writer.get_extra_info("sockname")
        server_port = server_info[1]

        logger.info(f"New connection from {addr} on port {server_port}")

        is_authenticated = False
        clientdata = None

        if server_port == 2776:
            client_dlr_status = "DELIVRD"
        elif server_port == 2777:
            client_dlr_status = "REJECTD"
        else:
            client_dlr_status = "UNKNOWN"

        try:
            while True:
                header_data = await reader.read(16)
                if not header_data or len(header_data) < 16:
                    break

                cmd_len, cmd_id, cmd_status, seq_num = struct.unpack(
                    ">IIII", header_data
                )
                body_len = cmd_len - 16
                body_data = await reader.read(body_len) if body_len > 0 else b""

                if cmd_id == CMD_BIND_TRANSCEIVER:
                    system_id, offset = self.read_c_string(body_data, 0)
                    password, offset = self.read_c_string(body_data, offset)

                    client_obj = await self.authenticate_client(system_id, password)
                    clientdata = client_obj

                    if client_obj:
                        is_authenticated = True
                        logger.info(f"Client bound and authenticated: {system_id}")
                        resp_body = system_id.encode("ascii") + b"\0"
                        await self.send_pdu(
                            writer,
                            CMD_BIND_TRANSCEIVER_RESP,
                            ESME_ROK,
                            seq_num,
                            resp_body,
                        )
                    else:
                        await self.send_pdu(
                            writer,
                            CMD_BIND_TRANSCEIVER_RESP,
                            0x0000000F,
                            seq_num,
                            b"\0",
                        )
                        break

                elif cmd_id == CMD_SUBMIT_SM:
                    if not is_authenticated:
                        await self.send_pdu(
                            writer, CMD_SUBMIT_SM_RESP, 0x00000004, seq_num, b""
                        )
                        continue

                    sms_info = self.parse_submit_sm(body_data)
                    msg_id_str = await self.generate_message_id()

                    # Handle Segmented Messages
                    if sms_info.get("is_segmented"):
                        ref = sms_info["ref_num"]
                        store_key = f"{sms_info['source']}_{sms_info['dest']}_{ref}"
                        if store_key not in self.message_store:
                            self.message_store[store_key] = {
                                "total": sms_info["total_parts"],
                                "parts": {},
                                "source": sms_info["source"],
                                "dest": sms_info["dest"],
                                "timestamp": time.time(),
                            }

                        self.message_store[store_key]["parts"][sms_info["part_num"]] = (
                            sms_info["text"]
                        )

                        if (
                            len(self.message_store[store_key]["parts"])
                            == self.message_store[store_key]["total"]
                        ):
                            # Reassemble
                            full_text = "".join(
                                [
                                    self.message_store[store_key]["parts"][i]
                                    for i in range(1, sms_info["total_parts"] + 1)
                                ]
                            )
                            sms_info["text"] = full_text
                            del self.message_store[store_key]  # Clean memory
                        else:
                            # Send partial ack
                            await self.send_pdu(
                                writer,
                                CMD_SUBMIT_SM_RESP,
                                ESME_ROK,
                                seq_num,
                                msg_id_str.encode() + b"\0",
                            )
                            logger.debug(
                                f"Received part {sms_info['part_num']} of {sms_info['total_parts']} (StoreKey: {store_key})"
                            )
                            continue
                    dest = sms_info["dest"]
                    # masked_dest = (
                    #     f"{dest[:5]}****{dest[-3:]}" if len(dest) > 8 else "***"
                    # )

                    msg_length = len(sms_info["text"])
                    # Message is Complete
                    logger.info(
                        f"MSG PROCESSED | From: {sms_info['source']} | To: {dest} | Length: {msg_length} chars"
                    )
                    # 3. Log full text ONLY at DEBUG level
                    # logger.debug(f"Full Message Content: {sms_info['text']}")

                    # Send Submit_SM_Resp
                    await self.send_pdu(
                        writer,
                        CMD_SUBMIT_SM_RESP,
                        ESME_ROK,
                        seq_num,
                        msg_id_str.encode() + b"\0",
                    )

                    # 🚀 FIRE AND FORGET! This runs in the background.
                    # The server immediately loops back to read the next SMPP packet!
                    asyncio.create_task(
                        self.process_and_receipt(
                            writer,
                            sms_info,
                            msg_id_str,
                            seq_num,
                            clientdata,
                            client_dlr_status,
                        )
                    )

                elif cmd_id == CMD_ENQUIRE_LINK:
                    await self.send_pdu(
                        writer, CMD_ENQUIRE_LINK_RESP, ESME_ROK, seq_num, b""
                    )

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Connection Error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    def parse_submit_sm(self, body):
        offset = 0
        _, offset = self.read_c_string(body, offset)  # service_type
        offset += 2  # ton/npi
        src, offset = self.read_c_string(body, offset)
        offset += 2  # ton/npi
        dst, offset = self.read_c_string(body, offset)

        esm_class = body[offset]
        offset += 3  # esm, proto, priority
        _, offset = self.read_c_string(body, offset)  # schedule
        _, offset = self.read_c_string(body, offset)  # validity
        offset += 2  # reg, replace
        data_coding = body[offset]
        offset += 2  # coding, default_msg_id

        sm_len = body[offset]
        offset += 1
        msg_bytes = body[offset : offset + sm_len]

        res = {"source": src, "dest": dst, "is_segmented": False, "text": ""}

        if esm_class & 0x40:
            udh_len = msg_bytes[0]
            if udh_len >= 5 and msg_bytes[1] == 0x00:  # 8-bit reference
                res["is_segmented"] = True
                res["ref_num"] = msg_bytes[3]
                res["total_parts"] = msg_bytes[4]
                res["part_num"] = msg_bytes[5]
            actual_bytes = msg_bytes[udh_len + 1 :]
        else:
            actual_bytes = msg_bytes

        try:
            if data_coding == 8:
                res["text"] = actual_bytes.decode("utf-16-be", errors="ignore")
            else:
                res["text"] = actual_bytes.decode("utf-8", errors="ignore")
        except:
            res["text"] = actual_bytes.decode("ascii", errors="ignore")

        return res

    async def send_dlr(self, writer, sms_info, fullmsg, msg_id, dlr_seq, dlr_status):
        timestamp = datetime.datetime.now().strftime("%y%m%d%H%M")

        # 1. Truncate the safe text to ensure the total DLR doesn't exceed 255
        # We leave about 100 chars for the headers (id, stat, date, etc.)
        full_safe_text = sms_info["text"].encode("ascii", "ignore").decode("ascii")[:40]

        if dlr_status == "DELIVRD":
            dlr_text = f"id:{msg_id} sub:001 dlvrd:001 submit date:{timestamp} done date:{timestamp} stat:{dlr_status} err:000 text:{full_safe_text}"
        elif dlr_status == "REJECTD":
            dlr_text = f"id:{msg_id} sub:000 dlvrd:000 submit date:{timestamp} done date:{timestamp} stat:{dlr_status} err:001 text:{full_safe_text}"

        dlr_bytes = dlr_text.encode("ascii", errors="ignore")

        # 2. Final safety check: hard truncate bytes to 255
        dlr_bytes = dlr_bytes[:255]

        body = b"\0"
        body += b"\x01\x01" + sms_info["dest"].encode("ascii", "ignore") + b"\0"
        body += b"\x01\x01" + sms_info["source"].encode("ascii", "ignore") + b"\0"
        body += b"\x04"  # esm_class: Delivery Receipt
        body += b"\0" * 7
        body += b"\0"
        body += struct.pack("B", len(dlr_bytes))  # Now len is guaranteed <= 255
        body += dlr_bytes

        await self.send_pdu(writer, CMD_DELIVER_SM, ESME_ROK, dlr_seq, body)

    async def send_pdu(self, writer, cmd_id, status, seq, body):
        length = 16 + len(body)
        header = struct.pack(">IIII", length, cmd_id, status, seq)
        # ADD THIS: Wait for the green light before writing to the socket
        async with writer.write_lock:
            writer.write(header + body)
            await writer.drain()

    def read_c_string(self, data, offset):
        end = data.find(b"\0", offset)
        if end == -1:
            return "", len(data)
        return data[offset:end].decode("ascii", errors="ignore"), end + 1
