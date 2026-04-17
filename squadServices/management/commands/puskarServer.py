import asyncio
import struct
import logging
import datetime
from django.core.management.base import BaseCommand
import uuid
from asgiref.sync import sync_to_async
from django.db.models import Q
import requests

from squadServices.models.clientModel.client import Client

# Configuration
HOST = "0.0.0.0"
PORT = 2776
HOST1 = "0.0.0.0"
PORT1 = 2777
# SMPP Command IDs
CMD_BIND_TRANSCEIVER = 0x00000009
CMD_BIND_TRANSCEIVER_RESP = 0x80000009
CMD_SUBMIT_SM = 0x00000004
CMD_SUBMIT_SM_RESP = 0x80000004
CMD_DELIVER_SM = 0x00000005
CMD_ENQUIRE_LINK = 0x00000015
CMD_ENQUIRE_LINK_RESP = 0x80000015

# SMPP Status
ESME_ROK = 0x00000000
mainStatus = "delivered"
logger = logging.getLogger(__name__)
clientdata = None
message_id = 0


def callApi(sms_text, destination, source, client_dlr_status):
    print("===============================================")
    if client_dlr_status == "DELIVRD":
        api = "https://boss.arssapp.com/sms_test/api/sms/deliverAdd"
    else:
        api = "https://boss.arssapp.com/sms_test/api/sms/deliveryFailedAdd"

    print("sms_text", sms_text)
    print("destination", destination)
    print("source", source)
    payload = {"messageContent": sms_text, "toUser": destination, "userID": source.id}
    res = requests.post(api, json=payload)
    print(
        "============== res.status_code=================================",
        res.status_code,
    )

    print("API Response:", res.status_code, res.text)
    return res


class Command(BaseCommand):
    help = "SMPP Server: Collects all segments then prints full SMS and sends DLR"

    # In-memory store for concatenated messages
    # Structure: { ref_num: { "total": int, "parts": { part_num: text }, "source": str, "dest": str } }
    message_store = {}

    async def generate_message_id(self):  # If it has 'async'
        return str(uuid.uuid4())

    def handle(self, *args, **kwargs):
        self.stdout.write(
            self.style.SUCCESS(f"Starting SMPP Server on {HOST}:{PORT}...")
        )
        try:
            asyncio.run(self.run_server())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nServer stopped."))

    @sync_to_async
    def authenticate_client(self, username, password):
        """
        Strictly handles authentication. We don't route yet because
        we don't know the destination number until the SUBMIT_SM command!
        """
        print(f"Authenticating client: {username}")
        print(f"Password provided: {password}")
        try:
            client = Client.objects.filter(
                (Q(DsmppUsername=username) | Q(FsmppUsername=username)),
                smppPassword=password,
                isDeleted=False,
            ).first()

            # ⚡️ 1. First, check if the client actually exists!
            if not client:
                logger.warning(
                    f"Auth Failed: Invalid credentials or deleted account for '{username}'."
                )
                return None

            # ⚡️ 2. Now it is safe to check the status if you need to
            clientStatus = client.status

            return client

        except Exception as e:
            logger.error(f"Auth Lookup Error for '{username}': {e}")
            return None

    async def run_server(self):
        server1 = await asyncio.start_server(self.handle_client, HOST, PORT)
        self.stdout.write(f"Server 1 listening on {HOST}:2776")
        server2 = await asyncio.start_server(self.handle_client, HOST1, PORT1)
        self.stdout.write(f"Server 2 listening on {HOST1}:2777")
        async with server1, server2:
            await asyncio.gather(server1.serve_forever(), server2.serve_forever())

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info("peername")
        logger.info(f"New connection from {addr}")
        is_authenticated = False
        # 1. Get the Client's IP Address
        client_addr = writer.get_extra_info("peername")

        # 2. ⚡️ Get the SERVER's Port that the client connected to!
        server_info = writer.get_extra_info("sockname")
        server_port = server_info[1]  # This will be 2776 or 2777
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
                        # ⚡️ If auth fails, send an error (0x0F) and disconnect them!
                        await self.send_pdu(
                            writer,
                            CMD_BIND_TRANSCEIVER_RESP,
                            0x0000000F,
                            seq_num,
                            b"\0",
                        )
                        break
                    logger.info(f"Client authenticated: {system_id}")
                    logger.info(f"Client bound: {system_id}")
                    resp_body = system_id.encode("ascii") + b"\0"
                    await self.send_pdu(
                        writer, CMD_BIND_TRANSCEIVER_RESP, ESME_ROK, seq_num, resp_body
                    )

                elif cmd_id == CMD_SUBMIT_SM:

                    if not is_authenticated:
                        await self.send_pdu(
                            writer, CMD_SUBMIT_SM_RESP, 0x00000004, seq_num, b""
                        )
                        continue

                    # 1. Parse current PDU
                    sms_info = self.parse_submit_sm(body_data)
                    print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!,${sms_info['text']}")
                    message_id = await self.generate_message_id()
                    msg_id_str = message_id

                    # 2. Logic: Is this a fragment or a single message?
                    if sms_info.get("is_segmented"):
                        ref = sms_info["ref_num"]

                        if ref not in self.message_store:
                            self.message_store[ref] = {
                                "total": sms_info["total_parts"],
                                "parts": {},
                                "source": sms_info["source"],
                                "dest": sms_info["dest"],
                            }

                        # Store this specific part
                        self.message_store[ref]["parts"][sms_info["part_num"]] = (
                            sms_info["text"]
                        )

                        # Check if we have received all pieces
                        if (
                            len(self.message_store[ref]["parts"])
                            == self.message_store[ref]["total"]
                        ):
                            # REASSEMBLE FULL TEXT
                            full_text = "".join(
                                [
                                    self.message_store[ref]["parts"][i]
                                    for i in range(1, sms_info["total_parts"] + 1)
                                ]
                            )
                            sms_info["text"] = full_text

                            # Clean memory
                            del self.message_store[ref]
                        else:
                            # PARTIAL: Send Submit_SM_Resp (Ack) but NO PRINT and NO DLR
                            await self.send_pdu(
                                writer,
                                CMD_SUBMIT_SM_RESP,
                                ESME_ROK,
                                seq_num,
                                msg_id_str.encode() + b"\0",
                            )
                            logger.info(
                                f"Received part {sms_info['part_num']} of {sms_info['total_parts']} (Ref: {ref})"
                            )
                            continue

                    # 3. FINAL ACTION: Message is complete (or was never segmented)
                    print("\n" + "=" * 40)
                    print(f"COMPLETE MESSAGE RECEIVED")
                    print(f"From: {sms_info['source']}")
                    print(f"To:   {sms_info['dest']}")
                    print(f"Msg:  {sms_info['text']}")
                    print("=" * 40 + "\n")

                    # Send Response for the final segment
                    await self.send_pdu(
                        writer,
                        CMD_SUBMIT_SM_RESP,
                        ESME_ROK,
                        seq_num,
                        msg_id_str.encode() + b"\0",
                    )

                    destination = sms_info["dest"]
                    sms_text = sms_info["text"]
                    print(
                        "data==========messageContent==msg_id_strmsg_id_strmsg_id_strmsg_id_str========",
                        clientdata,
                    )
                    response = callApi(
                        sms_text, destination, clientdata, client_dlr_status
                    )
                    if response.status_code == 406:
                        print("⚠️ SQUAD SERVER REJECTED MESSAGE: Subscription Expired")
                        await self.send_pdu(
                            writer,
                            CMD_SUBMIT_SM_RESP,
                            0x00000045,  # ESME_RBINDFAIL or 0x0000000B (Queue Full)
                            seq_num,
                            b"\0",
                        )
                        # Optionally skip sending the DLR since the message failed
                        return

                    print(response.status_code)
                    print(response.json())

                    # Send Success DLR (only once for the whole message)
                    await self.send_dlr(
                        writer,
                        sms_info,
                        sms_info["text"],
                        msg_id_str,
                        seq_num + 1000,
                        client_dlr_status,
                    )

                elif cmd_id == CMD_ENQUIRE_LINK:
                    await self.send_pdu(
                        writer, CMD_ENQUIRE_LINK_RESP, ESME_ROK, seq_num, b""
                    )

        except Exception as e:
            logger.error(f"Error: {e}")
        finally:
            writer.close()

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

        # UDH Check (Bit 6 of esm_class)
        if esm_class & 0x40:
            udh_len = msg_bytes[0]
            if udh_len >= 5 and msg_bytes[1] == 0x00:  # 8-bit reference
                res["is_segmented"] = True
                res["ref_num"] = msg_bytes[3]
                res["total_parts"] = msg_bytes[4]
                res["part_num"] = msg_bytes[5]

            # Text starts after the UDH
            actual_bytes = msg_bytes[udh_len + 1 :]
        else:
            actual_bytes = msg_bytes

        # Decoding
        try:
            if data_coding == 8:
                res["text"] = actual_bytes.decode("utf-16-be", errors="ignore")
                print(f"Decoded as UCS2: {res['text']}")
            else:
                res["text"] = actual_bytes.decode("utf-8", errors="ignore")
        except:
            res["text"] = actual_bytes.decode("ascii", errors="ignore")

        return res

    async def send_dlr(self, writer, sms_info, fullmsg, msg_id, dlr_seq, dlr_status):
        timestamp = datetime.datetime.now().strftime("%y%m%d%H%M")
        # Clean text for DLR metadata (ASCII only)
        print("stauts======!!!!!!!!!!!!!!!!!!!!!!!!!!!!=====", mainStatus)
        full_safe_text = sms_info["text"].encode("ascii", "ignore").decode("ascii")
        if dlr_status == "DELIVRD":
            dlr_text = (
                f"id:{msg_id} sub:001 dlvrd:001 submit date:{timestamp} "
                f"done date:{timestamp} stat:{dlr_status} err:000 text:{full_safe_text} fulltext:{fullmsg}"
            )

        elif dlr_status == "REJECTD":
            dlr_text = (
                f"id:{msg_id} sub:000 dlvrd:000 submit date:{timestamp} "
                f"done date:{timestamp} stat:{dlr_status} err:001 text:{full_safe_text} fulltext:{fullmsg}"
            )
        # ⚡️ INJECT dlr_status INTO THE STRING HERE

        dlr_bytes = dlr_text.encode("ascii", errors="ignore")

        body = b"\0"
        body += b"\x01\x01" + sms_info["dest"].encode("ascii", "ignore") + b"\0"
        body += b"\x01\x01" + sms_info["source"].encode("ascii", "ignore") + b"\0"
        body += b"\x04"  # esm_class: Delivery Receipt
        body += b"\0" * 7
        body += b"\0"
        body += struct.pack("B", len(dlr_bytes))
        body += dlr_bytes

        await self.send_pdu(writer, CMD_DELIVER_SM, ESME_ROK, dlr_seq, body)

    async def send_pdu(self, writer, cmd_id, status, seq, body):
        length = 16 + len(body)
        header = struct.pack(">IIII", length, cmd_id, status, seq)
        writer.write(header + body)
        await writer.drain()

    def read_c_string(self, data, offset):
        end = data.find(b"\0", offset)
        if end == -1:
            return "", len(data)
        return data[offset:end].decode("ascii", errors="ignore"), end + 1
