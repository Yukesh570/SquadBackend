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
    message_store = {}
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
        # ⚡️ OPTIMIZATION: High-concurrency pool for the slow API (1.27s latency)
        connector = aiohttp.TCPConnector(limit=1000, ttl_dns_cache=300)
        # ⚡️ SAFETY: Strict timeout to prevent hanging background tasks
        timeout = aiohttp.ClientTimeout(total=15)
        self.http_session = aiohttp.ClientSession(connector=connector, timeout=timeout)

        cleanup_task = asyncio.create_task(self.cleanup_stale_messages())

        server1 = await asyncio.start_server(self.handle_client, HOST, PORT)
        server2 = await asyncio.start_server(self.handle_client, HOST1, PORT1)

        self.stdout.write(
            self.style.SUCCESS(f"Servers listening on {PORT} and {PORT1}")
        )

        try:
            async with server1, server2:
                await asyncio.gather(server1.serve_forever(), server2.serve_forever())
        finally:
            cleanup_task.cancel()
            await self.http_session.close()

    async def cleanup_stale_messages(self):
        """Background task to remove incomplete segmented messages."""
        while True:
            await asyncio.sleep(60)
            current_time = time.time()
            stale_refs = [
                ref
                for ref, data in self.message_store.items()
                if current_time - data["timestamp"] > self.MESSAGE_TIMEOUT
            ]

            for ref in stale_refs:
                logger.warning(f"CLEANUP | Dropping stale message Ref: {ref}")
                del self.message_store[ref]

    async def callApi(self, sms_text, destination, source, client_dlr_status):
        """Sends the HTTP webhook with latency tracking."""
        api = (
            "https://boss.arssapp.com/sms_test/api/sms/deliverAdd"
            if client_dlr_status == "DELIVRD"
            else "https://boss.arssapp.com/sms_test/api/sms/deliveryFailedAdd"
        )

        payload = {
            "messageContent": sms_text,
            "toUser": destination,
            "userID": source.id,
        }

        start_time = time.time()
        try:
            async with self.http_session.post(api, json=payload) as res:
                await res.read()
                duration = time.time() - start_time

                # ⚡️ DEBUG: Identifying slow API responses
                if duration > 2.0:
                    logger.warning(
                        f"🐢 SLOW API | {duration:.2f}s | To: {destination} | Status: {res.status}"
                    )

                class DummyResponse:
                    status_code = res.status

                return DummyResponse()

        except asyncio.TimeoutError:
            logger.error(
                f"🚨 API TIMEOUT | {destination} | API failed to respond within 15s"
            )

            class DummyResponse:
                status_code = 504

            return DummyResponse()
        except Exception as e:
            logger.error(f"❌ API ERROR | {destination} | {str(e)}")

            class DummyResponse:
                status_code = 500

            return DummyResponse()

    async def background_task_wrapper(
        self, writer, sms_info, msg_id_str, seq_num, clientdata, client_dlr_status
    ):
        """Ensures background tasks are logged if they crash."""
        try:
            await self.process_and_receipt(
                writer, sms_info, msg_id_str, seq_num, clientdata, client_dlr_status
            )
        except Exception as e:
            logger.error(f"🚨 TASK CRASH | Msg {msg_id_str} | {str(e)}")

    async def process_and_receipt(
        self, writer, sms_info, msg_id_str, seq_num, clientdata, client_dlr_status
    ):
        response = await self.callApi(
            sms_info["text"], sms_info["dest"], clientdata, client_dlr_status
        )

        if response.status_code == 406:
            logger.warning(f"REJECTED | Subscription Expired for {msg_id_str}")
            return

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
        try:
            return PuskarClient.objects.filter(
                (Q(DsmppUsername=username) | Q(FsmppUsername=username)),
                smppPassword=password,
                isDeleted=False,
            ).first()
        except Exception as e:
            logger.error(f"DB ERROR | Auth Failed: {e}")
            return None

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info("peername")
        writer.write_lock = asyncio.Lock()
        server_port = writer.get_extra_info("sockname")[1]

        logger.info(f"CONN | New connection from {addr} on port {server_port}")
        client_dlr_status = (
            "DELIVRD"
            if server_port == 2776
            else "REJECTD" if server_port == 2777 else "UNKNOWN"
        )
        is_authenticated = False
        client_obj = None

        try:
            while True:
                # ⚡️ SOCKET TIMEOUT: 120s idle limit
                header_data = await asyncio.wait_for(reader.read(16), timeout=120.0)
                if not header_data or len(header_data) < 16:
                    break

                cmd_len, cmd_id, cmd_status, seq_num = struct.unpack(
                    ">IIII", header_data
                )
                body_len = cmd_len - 16
                body_data = await reader.read(body_len) if body_len > 0 else b""

                if cmd_id == CMD_BIND_TRANSCEIVER:
                    sys_id, offset = self.read_c_string(body_data, 0)
                    pwd, _ = self.read_c_string(body_data, offset)
                    client_obj = await self.authenticate_client(sys_id, pwd)

                    if client_obj:
                        is_authenticated = True
                        logger.info(f"AUTH | '{sys_id}' connected.")
                        await self.send_pdu(
                            writer,
                            CMD_BIND_TRANSCEIVER_RESP,
                            ESME_ROK,
                            seq_num,
                            sys_id.encode() + b"\0",
                        )
                    else:
                        logger.warning(f"AUTH | Failed login attempt for '{sys_id}'")
                        await self.send_pdu(
                            writer, CMD_BIND_TRANSCEIVER_RESP, 0x0F, seq_num, b"\0"
                        )
                        break

                elif cmd_id == CMD_SUBMIT_SM:
                    if not is_authenticated:
                        await self.send_pdu(
                            writer, CMD_SUBMIT_SM_RESP, 0x04, seq_num, b""
                        )
                        continue

                    sms_info = self.parse_submit_sm(body_data)
                    msg_id_str = await self.generate_message_id()

                    if sms_info.get("is_segmented"):
                        ref = sms_info["ref_num"]
                        store_key = f"{sms_info['source']}_{sms_info['dest']}_{ref}"
                        if store_key not in self.message_store:
                            self.message_store[store_key] = {
                                "total": sms_info["total_parts"],
                                "parts": {},
                                "timestamp": time.time(),
                            }

                        self.message_store[store_key]["parts"][sms_info["part_num"]] = (
                            sms_info["text"]
                        )

                        if (
                            len(self.message_store[store_key]["parts"])
                            == self.message_store[store_key]["total"]
                        ):
                            full_text = "".join(
                                [
                                    self.message_store[store_key]["parts"][i]
                                    for i in range(1, sms_info["total_parts"] + 1)
                                ]
                            )
                            sms_info["text"] = full_text
                            del self.message_store[store_key]
                        else:
                            await self.send_pdu(
                                writer,
                                CMD_SUBMIT_SM_RESP,
                                ESME_ROK,
                                seq_num,
                                msg_id_str.encode() + b"\0",
                            )
                            continue

                    logger.info(
                        f"SUCCESS | Processed: {msg_id_str} | To: {sms_info['dest']}"
                    )
                    await self.send_pdu(
                        writer,
                        CMD_SUBMIT_SM_RESP,
                        ESME_ROK,
                        seq_num,
                        msg_id_str.encode() + b"\0",
                    )

                    # ⚡️ ASYNC WRAPPER: Fire background task for slow API
                    asyncio.create_task(
                        self.background_task_wrapper(
                            writer,
                            sms_info,
                            msg_id_str,
                            seq_num,
                            client_obj,
                            client_dlr_status,
                        )
                    )

                elif cmd_id == CMD_ENQUIRE_LINK:
                    await self.send_pdu(
                        writer, CMD_ENQUIRE_LINK_RESP, ESME_ROK, seq_num, b""
                    )

        except asyncio.TimeoutError:
            logger.warning(f"TIMEOUT | Connection {addr} idle too long.")
        except Exception as e:
            logger.error(f"ERROR | Connection {addr}: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    def parse_submit_sm(self, body):
        offset = 0
        _, offset = self.read_c_string(body, offset)
        offset += 2
        src, offset = self.read_c_string(body, offset)
        offset += 2
        dst, offset = self.read_c_string(body, offset)
        esm_class = body[offset]
        offset += 3
        _, offset = self.read_c_string(body, offset)
        _, offset = self.read_c_string(body, offset)
        offset += 2
        data_coding = body[offset]
        offset += 2
        sm_len = body[offset]
        offset += 1
        msg_bytes = body[offset : offset + sm_len]
        res = {"source": src, "dest": dst, "is_segmented": False, "text": ""}
        if esm_class & 0x40:
            udh_len = msg_bytes[0]
            if udh_len >= 5 and msg_bytes[1] == 0x00:
                res["is_segmented"] = True
                res["ref_num"] = msg_bytes[3]
                res["total_parts"] = msg_bytes[4]
                res["part_num"] = msg_bytes[5]
            actual_bytes = msg_bytes[udh_len + 1 :]
        else:
            actual_bytes = msg_bytes
        try:
            res["text"] = actual_bytes.decode(
                "utf-16-be" if data_coding == 8 else "utf-8", errors="ignore"
            )
        except:
            res["text"] = actual_bytes.decode("ascii", errors="ignore")
        return res

    async def send_dlr(self, writer, sms_info, fullmsg, msg_id, dlr_seq, dlr_status):
        timestamp = datetime.datetime.now().strftime("%y%m%d%H%M")
        full_safe_text = sms_info["text"].encode("ascii", "ignore").decode("ascii")[:40]
        dlr_text = f"id:{msg_id} sub:00{'1' if dlr_status == 'DELIVRD' else '0'} dlvrd:00{'1' if dlr_status == 'DELIVRD' else '0'} submit date:{timestamp} done date:{timestamp} stat:{dlr_status} err:000 text:{full_safe_text}"
        dlr_bytes = dlr_text.encode("ascii", errors="ignore")[:255]
        body = (
            b"\0"
            + b"\x01\x01"
            + sms_info["dest"].encode("ascii", "ignore")
            + b"\0"
            + b"\x01\x01"
            + sms_info["source"].encode("ascii", "ignore")
            + b"\0"
            + b"\x04"
            + b"\0" * 7
            + b"\0"
            + struct.pack("B", len(dlr_bytes))
            + dlr_bytes
        )
        await self.send_pdu(writer, CMD_DELIVER_SM, ESME_ROK, dlr_seq, body)

    async def send_pdu(self, writer, cmd_id, status, seq, body):
        length = 16 + len(body)
        header = struct.pack(">IIII", length, cmd_id, status, seq)
        async with writer.write_lock:
            writer.write(header + body)
            await writer.drain()

    def read_c_string(self, data, offset):
        end = data.find(b"\0", offset)
        if end == -1:
            return "", len(data)
        return data[offset:end].decode("ascii", errors="ignore"), end + 1
