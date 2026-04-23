# myapp/management/commands/run_smpp_server.py
from ast import If
import asyncio
from csv import writer
import hashlib
import math
import os
import struct
import logging
from django.core.management.base import BaseCommand
from asgiref.sync import sync_to_async
from django.utils import timezone
from squadServices.helper.checkNumber import clean_phone_number
from squadServices.helper.routeAndCostHelper import get_route_and_cost
from squadServices.helper.smsSplitter import (
    create_message_parts,
    create_message_parts_when_failed,
)
from squadServices.models.clientModel.client import Client, ClientSession, IpWhitelist
from squadServices.models.connectivityModel.smpp import SMPP
import secrets
from squadServices.models.connectivityModel.verdor import Vendor
from squadServices.models.country import Country
from squadServices.models.detailedReport.detailedReport import DetailedSMSReport
from squadServices.models.operators.operators import Operators
from squadServices.models.routeManager.customRoute import CustomRoute
from squadServices.models.smpp.smppSMS import SMSMessage, SMSMessagePart
import re
from django.db import transaction
from datetime import timedelta
from squadServices.models.transaction.transaction import (
    ClientTransaction,
    TransactionType,
    VendorTransaction,
)
import uuid
import redis.asyncio as redis
from channels.layers import get_channel_layer
from logging.handlers import RotatingFileHandler

# from squadServices.models.transaction import transaction

# Configuration
# HOST = "192.168.10.3"
HOST = "0.0.0.0"
PORT = 2775

# SMPP Command IDs
CMD_BIND_RECEIVER = 0x00000001  # this is the command that a client sends to your server when they want to log in as a Receiver (listen-only).
CMD_BIND_TRANSMITTER = 0x00000002
CMD_BIND_TRANSCEIVER = 0x00000009
CMD_SUBMIT_SM = 0x00000004  # this is the command that the client sends to your server when they want to send an SMS. It contains all the details of the message, including the destination number, the text, and whether they want a DLR or not.
CMD_ENQUIRE_LINK = 0x00000015
CMD_DELIVER_SM = 0x00000005
# Response IDs (Request ID + 0x80000000)
CMD_BIND_RECEIVER_RESP = 0x80000001
CMD_BIND_TRANSMITTER_RESP = 0x80000002
CMD_BIND_TRANSCEIVER_RESP = 0x80000009
CMD_SUBMIT_SM_RESP = 0x80000004
CMD_ENQUIRE_LINK_RESP = 0x80000015
CMD_DELIVER_SM_RESP = 0x80000005  # <--- ADD THIS LINE
CMD_GENERIC_NACK = 0x80000000

# SMPP Status
ESME_ROK = 0x00000000

logger = logging.getLogger(__name__)

# --- CREATE A DEDICATED FILE LOGGER FOR SMPP TRAFFIC ---
# 1. Create a logs folder if it doesn't exist
if not os.path.exists("logs"):
    os.makedirs("logs")

# 2. Set up the specific logger
traffic_logger = logging.getLogger("smpp_traffic")
traffic_logger.setLevel(logging.INFO)
traffic_logger.propagate = False  # Prevents these logs from spamming your main console

# 3. Create the Rotating File Handler (Max 5MB per file, keeps 5 backups)
file_handler = RotatingFileHandler(
    "logs/smpp_traffic.log", maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
)

# 4. Set the exact format for the file (adds Date and Time automatically!)
formatter = logging.Formatter("%(asctime)s - [%(levelname)s] - %(message)s")
file_handler.setFormatter(formatter)

if not traffic_logger.handlers:
    traffic_logger.addHandler(file_handler)


# --------------------------------------------------------
class Command(BaseCommand):
    help = "Runs a lightweight SMPP Server to receive SMS"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_clients = {}  # Dictionary to hold open TCP connections
        self.route_cache = {}  # ⚡️ ADD THIS

    async def generate_message_id(self):  # If it has 'async'
        return str(uuid.uuid4())

    def detect_encoding(self, text):
        """Detect if text is GSM-7 compatible or requires UCS-2"""
        gsm7_basic = (
            "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./"
            "0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§"
            "¿abcdefghijklmnopqrstuvwxyzäöñüà"
        )
        gsm7_ext = "^{}\\[~]|€"

        for char in text:
            if char not in gsm7_basic and char not in gsm7_ext:
                return "UCS-2"
        return "GSM-7"

    def calculate_segments(self, text, encoding):
        length = len(text)

        if encoding == "GSM-7":
            if length <= 160:
                return 1, length
            else:
                return math.ceil(length / 153), length
        else:  # UCS-2
            if length <= 70:
                return 1, length
            else:
                return math.ceil(length / 67), length

    @sync_to_async
    def save_failed_routing_attempt(
        self,
        client_obj,
        destination_addr,
        short_message,
        encoding_type,
        total_segments,
        total_chars,
        source_addr,
        unique_msg_id,
        error_reason,
        want_dlr,
    ):
        now = timezone.now()
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("!!!!!!22323232ppppp!!!!!!!!!!!!!!!!!!!!!!!!!!!!", client_obj)

        # 1. Create the parent message as FAILED (Same as before)
        msg = SMSMessage.objects.create(
            client=client_obj,
            systemId=client_obj.smppUsername,
            message_id=unique_msg_id,
            characterCount=total_chars,
            destination=destination_addr,
            text=short_message,
            encoding=encoding_type,
            segmentNumber=total_segments,
            status="failed",  # ⚡️ Starts and ends as failed
            failure_reason=error_reason,
            failed_at=now,
            queued_at=now,
            sendClientDlr=want_dlr,
        )
        print("!!!!!222!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

        print("!!!!3333!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

        # 3. ⚡️ CALL YOUR MAGIC FUNCTION ⚡️
        create_message_parts_when_failed(
            sms_message_obj=msg,
            text=short_message,
            initial_status="FAILED",
            fail_reason=error_reason,
        )

    @sync_to_async
    def check_ip_whitelist(self, ip_address, client_obj=None):
        """
        If client_obj is provided, check if the IP belongs to that specific client.
        Otherwise, check if the IP is whitelisted at all.
        """
        if client_obj:
            return IpWhitelist.objects.filter(
                ip=ip_address, client=client_obj, isDeleted=False
            ).exists()
        return IpWhitelist.objects.filter(ip=ip_address, isDeleted=False).exists()

    @sync_to_async
    def reap_stale_messages(self):
        """
        Production Reaper: Sweeps messages stuck in 'queued' beyond the timeout threshold
        and marks them as failed due to vendor unresponsiveness.
        """
        # Define the maximum time a message is allowed to wait for a vendor (e.g., 5 minutes)
        timeout_threshold = timezone.now() - timedelta(seconds=5)
        stale_msgs = SMSMessage.objects.filter(
            status="queued",
            queued_at__lte=timeout_threshold,
            sendClientDlr=True,
            clientDlrPushed=False,
        )

        reaped_count = stale_msgs.count()
        if reaped_count == 0:
            return  # Exit cleanly if nothing is stuck

        for msg in stale_msgs:
            msg.status = "failed"
            msg.failure_reason = "Reaper Timeout: Message was stuck in queue too long."  # Update failure_reason
            msg.save(update_fields=["status", "failure_reason"])
            # 2. ---> NEW: Instantly fail all associated parts <---
            # This prevents the background worker from ever picking them up
            SMSMessagePart.objects.filter(message=msg).update(
                submit_status="FAILED",
                failed_at=timezone.now(),
                failure_reason="Reaper Timeout: Message was stuck in queue too long.",
            )

            # Create an official DLR event for the timeout (408 Request Timeout)
            msg.dlrevent_set.create(
                status_code="408",
            )

        # Log the failure professionally on the server
        logger.error(
            f"Gateway Timeout: {reaped_count} queued messages marked FAILED due to vendor unresponsiveness."
        )

    @sync_to_async
    def authenticate_client(self, username, password):
        """
        Strictly handles authentication. We don't route yet because
        we don't know the destination number until the SUBMIT_SM command!
        """
        try:
            client = Client.objects.filter(
                smppUsername=username, smppPassword=password, isDeleted=False
            ).first()
            clientStatus = client.status
            if not client:
                logger.warning(
                    f"Auth Failed: Invalid credentials or deleted account for '{username}'."
                )
                return None

            # if client.status not in ["ACTIVE", "TRIAL"]:
            #     logger.warning(
            #         f"Auth Failed: Account '{username}' is currently {client.status}."
            #     )

            #     return None

            return client
        except Exception as e:
            logger.error(f"Auth Lookup Error for '{username}': {e}")
            return None

    @sync_to_async
    def register_client_session(self, client_obj, system_id, bind_cmd_id, ip, port):
        """Creates a new session row when a client successfully binds."""
        bind_map = {
            0x00000001: "RECEIVER",
            0x00000002: "TRANSMITTER",
            0x00000009: "TRANSCEIVER",
        }
        bind_type = bind_map.get(bind_cmd_id, "UNKNOWN")

        session = ClientSession.objects.create(
            client=client_obj,
            systemId=system_id,
            bindType=bind_type,
            remoteIp=ip,
            remotePort=port,
            status="ONLINE",
        )
        return session.sessionId

    @sync_to_async
    def update_session_activity(self, session_id):
        """Updates the last_activityAt timestamp when a heartbeat is received."""
        if session_id:
            ClientSession.objects.filter(sessionId=session_id).update(status="ONLINE")

    @sync_to_async
    def close_client_session(self, session_id):
        """Marks the session as OFFLINE when the socket closes."""
        if session_id:
            ClientSession.objects.filter(sessionId=session_id).update(status="OFFLINE")

    def handle(self, *args, **kwargs):
        self.stdout.write(f"Starting SMPP Server on {HOST}:{PORT}...")
        try:
            asyncio.run(self.run_server())
        except KeyboardInterrupt:
            self.stdout.write("Server stopped.")

    # Once the server is running, it just waits.
    # The moment an external client (like another SMPP server or SMS gateway) connects to your port

    async def run_server(self):

        # 🧹 Reset everyone to OFFLINE on server boot to prevent Zombies
        await sync_to_async(Client.objects.all().update)(bindStatus="OFFLINE")
        redis_host = os.environ.get("REDIS_HOST", "redis")
        # ⚡️ Using DB=1 keeps our SMPP buffer strictly separated from Celery (DB=0)
        self.redis_client = redis.Redis(
            host=redis_host, port=6379, db=1, decode_responses=True
        )
        # Even if 1,000 clients are connected to your server at the same time, the server doesn't get confused
        # When a new client connects, the Python asyncio library creates a unique instance
        # of a StreamWriter just for that specific socket.
        # Client A connects The server runs handle_client and gives it writer_A.
        # Client B connects The server runs a separate instance of handle_client and gives it writer_B
        server = await asyncio.start_server(self.handle_client, HOST, PORT)
        # --- 2. START THE BACKGROUND LOOP HERE ---
        asyncio.create_task(self.dlr_dispatcher_loop())
        async with server:
            await server.serve_forever()

    async def broadcast_session_update(
        self, session_id, system_id, ip, port, bind_cmd_id, status
    ):
        """Broadcasts live session changes to the Django Channels WebSocket."""
        from channels.layers import get_channel_layer

        # Map the command ID to a readable bind type for the frontend
        bind_map = {
            0x00000001: "RECEIVER",
            0x00000002: "TRANSMITTER",
            0x00000009: "TRANSCEIVER",
        }
        bind_type = bind_map.get(bind_cmd_id, "UNKNOWN")

        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            "dashboard_updates",
            {
                "type": "session_change",  # ⚡️ Triggers session_change in consumers.py
                "session_id": str(session_id),
                "system_id": system_id,
                "ip": ip,
                "port": port,
                "bind_type": bind_type,
                "status": status,
            },
        )

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info("peername")
        client_ip = addr[0]
        client_port = addr[1]
        logger.info(f"New connection from {addr}")
        # --- 3. TRACK THE SYSTEM ID ---
        system_id_logged_in = None
        # ------------------------------
        try:
            while True:
                # 1. Read SMPP Header
                header_data = await reader.read(16)
                if not header_data or len(header_data) < 16:

                    # it then goes to finally
                    break

                cmd_len, cmd_id, cmd_status, seq_num = struct.unpack(
                    ">IIII", header_data
                )

                # 2. Read Body
                body_len = cmd_len - 16
                body_data = await reader.read(body_len) if body_len > 0 else b""

                # =========================================================
                # ⚡️ THE RAW PACKET LOGS (EXACTLY AS IT HIT THE SERVER)
                # =========================================================
                if cmd_id not in [0x00000015, 0x80000015]:  # Ignore Enquire Links
                    log_entry = [
                        f"RAW SMPP PACKET FROM {client_ip}",
                        f"Command   : {hex(cmd_id)} ({'SUBMIT_SM' if cmd_id == 0x4 else 'BIND' if cmd_id == 0x9 else 'OTHER'})",
                        f"Sequence  : {seq_num}",
                    ]

                    if cmd_id == 0x00000004:  # If it's a SUBMIT_SM
                        # 1. Grab the basic strings (Phone numbers) just for quick reference
                        c_strings = re.findall(b"[^\x00-\x1f\x7f-\xff]{3,}", body_data)
                        src = (
                            c_strings[0].decode("ascii", errors="ignore")
                            if len(c_strings) > 0
                            else "Unknown"
                        )
                        dest = (
                            c_strings[1].decode("ascii", errors="ignore")
                            if len(c_strings) > 1
                            else "Unknown"
                        )

                        log_entry.append(f"From      : {src}")
                        log_entry.append(f"To        : {dest}")

                        # 2. ⚡️ THE RAW BYTES
                        # This prints the pure Python byte string exactly as it arrived
                        log_entry.append(f"Raw Bytes : {body_data}")

                        # 3. ⚡️ THE HEX DUMP (Standard Telecom Debugging format)
                        # This formats the bytes into a clean, readable hex string (e.g. 00 05 53 51 55...)
                        readable_hex = " ".join(f"{b:02X}" for b in body_data)
                        log_entry.append(f"Raw Hex   : {readable_hex}")

                    # ⚡️ Write the entire block to the logs/smpp_traffic.log file!
                    traffic_logger.info("\n" + "\n".join(log_entry) + "\n" + "-" * 50)
                # ==============================================================================

                # 3. Handle BIND Commands

                # Before a client can send or receive any messages, they must authenticate (log in) with your server
                if cmd_id in [
                    CMD_BIND_RECEIVER,  # I am logging in strictly to listen for incoming messages and delivery receipts from you.
                    CMD_BIND_TRANSMITTER,  # The client is saying, "I am logging in strictly to send messages to you."
                    CMD_BIND_TRANSCEIVER,  # I want to do both
                ]:

                    # AUTHORIZATION COMES FIRST - We don't even care about the route until we know who they are!

                    system_id, offset = self.read_c_string(body_data, 0)
                    password, offset = self.read_c_string(body_data, offset)
                    print(f"Auth attempt: {system_id} from {client_ip}")

                    # NOW we can authenticate because system_id and password exist
                    client_obj = await self.authenticate_client(system_id, password)

                    if client_obj:
                        # policy = await sync_to_async(
                        #     lambda: getattr(client_obj, "clientPolicy", None)
                        # )()
                        # writer.policy = policy  # Attach it to the session

                        # # ⚡️ ENFORCE: Max Sessions Check
                        # # scans your server's memory to see how many times this specific client is already connected.

                        # # it count how many times the client is currently connected by looking at the active_clients dictionary,
                        # # Every time it finds the client from that specific client_obj, it counts 1 2 3....
                        # current_sessions = sum(
                        #     1
                        #     for w in self.active_clients.values()  # This looks at all currently connected clients
                        #     if getattr(w, "client_obj", None) == client_obj
                        # )

                        # # Then it checks if that counted number(current_sessions) exceeds the maxSessions limit defined in the client's policy.
                        # # If it does, it blocks the login attempt and sends back a specific error message (Status 8: Too Many Sessions).
                        # if current_sessions >= max_allowed:
                        #     logger.warning(
                        #         f"Blocking {system_id}: Too many active sessions ({current_sessions}/{max_allowed})"
                        #     )
                        #     await self.send_bind_error_with_tlv(
                        #         writer, cmd_id, 0x00000008, seq_num, "Too many sessions"
                        #     )
                        #     writer.close()
                        #     return

                        # print(
                        #     f"Current sessions for=========== {system_id}: {current_sessions}"
                        # )
                        # max_allowed = (
                        #     policy.maxSessions if policy else 2
                        # )  # default fallback
                        if client_obj.status not in ["ACTIVE", "TRIAL"]:
                            logger.warning(
                                f"Blocking {system_id}: Account is {client_obj.status}."
                            )

                            # Send Bind Failed (0x0D)
                            await self.send_bind_error_with_tlv(
                                writer,
                                cmd_id,
                                0x0000000D,  # 13 in decimal
                                seq_num,
                                f"Account {system_id} is {client_obj.status}. Please contact support.",
                            )
                            writer.close()
                            return
                        # Check IP Whitelist for this specific client
                        is_whitelisted = await self.check_ip_whitelist(
                            client_ip, client_obj=client_obj
                        )

                        if not is_whitelisted:
                            logger.warning(
                                f"Blocking {system_id}: IP {client_ip} not whitelisted."
                            )
                            # Send Bind Failed (0x0D) and close
                            await self.send_bind_error_with_tlv(
                                writer,
                                cmd_id,
                                0x0000000D,  # 13 in decimal
                                seq_num,
                                f"IP {client_ip} is not whitelisted for account {system_id}",
                            )

                            # await self.send_pdu(
                            #     writer, cmd_id | 0x80000000, 0x0000000D, seq_num, b""
                            # )
                            writer.close()
                            return

                        # SUCCESS
                        writer.is_authenticated = True
                        writer.client_obj = client_obj
                        # writer.vendor_obj = vendor_obj
                        # writer.smpp_obj = smpp_obj
                        system_id_logged_in = system_id
                        current_session_id = await self.register_client_session(
                            client_obj, system_id, cmd_id, client_ip, client_port
                        )
                        # when you run this db_session_id it is not saving in the global variable it is saving it in a isolated writer created specifically
                        # for that client connection, so when the next client connects it new writer
                        writer.db_session_id = current_session_id
                        self.active_clients[system_id] = writer
                        # 🚀 FIRE THE WEBSOCKET (Session Table Update)
                        await self.broadcast_session_update(
                            current_session_id,
                            system_id,
                            client_ip,
                            client_port,
                            cmd_id,
                            "ONLINE",
                        )
                        client_port = addr[1]

                        # ADD THIS: Flip the database switch to ONLINE
                        client_obj.bindStatus = "ONLINE"
                        await sync_to_async(client_obj.save)(
                            update_fields=["bindStatus"]
                        )
                        # BROADCAST ONLINE STATUS TO FRONTEND THAT A SESSION IS CREATED
                        channel_layer = get_channel_layer()
                        await channel_layer.group_send(
                            "dashboard_updates",
                            {
                                "type": "status_change",  # This triggers the status_change function in consumers.py!
                                "username": system_id_logged_in,
                                "status": "ONLINE",
                            },
                        )
                        resp_body = system_id.encode("ascii") + b"\0"
                        await self.send_pdu(
                            writer,
                            cmd_id | 0x80000000,
                            ESME_ROK,
                            seq_num,
                            resp_body,  # ESME_ROK means Successful authentication0
                        )
                        logger.info(f"Auth Success: {system_id}")
                    else:
                        # AUTH FAILURE
                        logger.warning(f"Auth Failed: {system_id}")
                        # ⚡️ THE FIX: Send the TLV explaining bad credentials (Status 15 / 0x0F)
                        await self.send_bind_error_with_tlv(
                            writer,
                            cmd_id,
                            0x0000000F,  # 15 in decimal
                            seq_num,
                            "Invalid Username or Password",
                        )
                        writer.close()
                        return
                elif (  # (Sending a Message)Here is a text message. Please route it and send it to this specific phone number.
                    cmd_id == CMD_SUBMIT_SM
                ):
                    # --- THE GUARD ---
                    if not getattr(writer, "is_authenticated", False):
                        logger.warning("Unauthenticated SUBMIT_SM attempt blocked.")
                        await self.send_pdu(
                            # CMD_SUBMIT_SM_RESP sends back the response to the client that sent the SUBMIT_SM command. We use it here to tell the client that their attempt was rejected due to lack of authentication.
                            writer,
                            CMD_SUBMIT_SM_RESP,
                            0x0000000F,
                            seq_num,
                            b"",
                        )
                        continue  # Changed from 'return' to 'continue' to keep connection open!
                    # -----------------

                    # 1. Handle the message and get the ID back
                    msg_id_to_return = await self.handle_submit_sm(
                        body_data, seq_num, writer
                    )

                    # # --- THE MISSING REJECTION LOGIC ---
                    # if not msg_id_to_return:
                    #     logger.warning("Rejecting PDU: Invalid Destination Address")
                    #     continue
                    # # -----------------------------------

                elif (
                    cmd_id == CMD_ENQUIRE_LINK
                ):  # TCP connections can drop if they sit idle for too long. ENQUIRE_LINK is a "ping" or "keep-alive" heartbeat.
                    # Keep-alive
                    await self.send_pdu(
                        writer, CMD_ENQUIRE_LINK_RESP, ESME_ROK, seq_num, b""
                    )
                    db_sess_id = getattr(writer, "db_session_id", None)
                    if db_sess_id:
                        await self.update_session_activity(db_sess_id)

                # i commented Because your script is acting as the SMPP Server, it should never accept a Delivery Receipt from a client. If they send one, it will now fall into the else: block and your server will correctly reject it with a Generic NACK error.
                # he DELIVER_SM command only flows in one direction: From the Server to the Client.
                elif (  # it talks to Your customers client (e.g., Acme Corp).
                    cmd_id == CMD_DELIVER_SM_RESP
                ):  # (Incoming Messages & Receipts) (This is a DLR)

                    pass

                    # 4. Respond to the carrier that you received the DLR

                else:
                    # Unknown command, send Generic NACK
                    await self.send_pdu(
                        writer, CMD_GENERIC_NACK, 0x00000003, seq_num, b""
                    )

        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            # --- 5. REMOVE THEM WHEN THEY DISCONNECT ---
            if system_id_logged_in and system_id_logged_in in self.active_clients:
                del self.active_clients[system_id_logged_in]

            # offline the client session in the database when they disconnect
            db_sess_id = getattr(writer, "db_session_id", None)
            if db_sess_id:
                await self.close_client_session(db_sess_id)
                # 🚀 FIRE THE WEBSOCKET (Session Table Update)
                old_cmd_id = getattr(
                    writer, "bind_cmd_id", 0
                )  # Grab the bind type we saved earlier
                await self.broadcast_session_update(
                    db_sess_id,
                    system_id_logged_in,
                    client_ip,
                    addr[1],
                    old_cmd_id,
                    "OFFLINE",
                )
            # 🔴 ADD THIS: Flip the database switch back to OFFLINE
            client_obj = getattr(writer, "client_obj", None)
            if client_obj:
                client_obj.bindStatus = "OFFLINE"
                # Use sync_to_async to safely hit the database when they drop
                await sync_to_async(client_obj.save)(update_fields=["bindStatus"])
                channel_layer = get_channel_layer()
                await channel_layer.group_send(
                    "dashboard_updates",
                    {
                        "type": "status_change",
                        "username": system_id_logged_in,
                        "status": "OFFLINE",
                    },
                )
                logger.info(f"{system_id_logged_in} went OFFLINE.")
            try:
                if not writer.is_closing():
                    writer.close()

                # Use a small timeout so we don't hang forever if the peer is dead
                await asyncio.wait_for(writer.wait_closed(), timeout=2.0)
            except (ConnectionResetError, BrokenPipeError, asyncio.TimeoutError):
                # We ignore these because they just mean the client hung up first
                pass
            except Exception as e:
                logger.debug(f"Quietly handled closing error: {e}")

    @sync_to_async
    def get_route_and_potential_cost(
        self, client_obj, destination_number, total_segments
    ):
        destination_country = None
        for i in range(4, 0, -1):
            possible_code = destination_number[:i]
            destination_country = Country.objects.filter(
                countryCode=possible_code, isDeleted=False
            ).first()
            if destination_country:
                break
        if not destination_country:
            return None, f"Unrecognized Country Code in {destination_number}"
        # --- 2. CHECK THE CACHE (Using the TRUE Country Code) ---
        # e.g., "client_5_44" or "client_5_57"
        cache_key = f"{client_obj.id}_{destination_country.countryCode}"
        if cache_key in self.route_cache:
            route_data = self.route_cache[cache_key].copy()  # Use cached data!
        else:

            # --- 2. CALL THE ROUTING ENGINE (No Operator Needed!) ---
            route_data, error = get_route_and_cost(client_obj, destination_country)

            if error:
                return None, error
            # Save it to RAM so the next 999 messages to Colombia are instant!
            self.route_cache[cache_key] = route_data

        # Multiply by segments to get true costs!
        total_vendor_cost = route_data["vendor_cost"] * total_segments
        total_client_cost = route_data["client_cost"] * total_segments

        terminating_company = route_data["terminatingCompany"]
        client_company = client_obj.company  # Get the Parent Company of the Client

        # 1. Check Vendor Limit (Does this push our debt to the vendor over the limit?)
        if (
            terminating_company.usedVendorCredit + total_vendor_cost
        ) > terminating_company.vendorCreditLimit:
            return None, "Insufficient Vendor Credit Line for multi-part message."

        # 2. Check Client Limit (Does this push the specific SMPP account over its limit?)
        if (client_obj.usedCredit + total_client_cost) > client_obj.creditLimit:
            return None, "Insufficient Client SMPP Credit Line for multi-part message."

        # 3. Check Global Company Limit (Does this push the Parent Company over its total limit?)
        if (
            client_company.usedCustomerCredit + total_client_cost
        ) > client_company.customerCreditLimit:
            return (
                None,
                "Insufficient Global Company Credit Line for multi-part message.",
            )

        route_data["total_vendor_cost"] = total_vendor_cost
        route_data["total_client_cost"] = total_client_cost

        return route_data, None

    # Switching back and forth between the async loop and synchronous DB threads is expensive.
    # You should combine these into a single transaction block inside one @sync_to_async function.
    # combined save_sms and perform_actual_deduction into one atomic function to improve TPS

    @sync_to_async
    def save_and_bill_sms_transaction(
        self,
        client_obj,
        route_data,
        destination,
        text,
        encodingType,
        total_segments,
        total_chars,
        source_addr,
        smpp,
        vendor,
        unique_msg_id,
        concat_ref,
        sendClientDlr,
    ):
        """Does EVERYTHING in a single, hyper-fast database lock."""
        raw_terminating_company = route_data["terminatingCompany"]
        raw_client_company = client_obj.company

        with transaction.atomic():
            # 1. LOCK BALANCES FIRST
            locked_terminating_company = (
                type(raw_terminating_company)
                .objects.select_for_update()
                .get(id=raw_terminating_company.id)
            )
            locked_client = Client.objects.select_for_update().get(id=client_obj.id)
            locked_client_company = (
                type(raw_client_company)
                .objects.select_for_update()
                .get(id=raw_client_company.id)
            )

            # 2. DEDUCT MONEY
            locked_terminating_company.usedVendorCredit += route_data[
                "total_vendor_cost"
            ]
            locked_terminating_company.save(update_fields=["usedVendorCredit"])

            locked_client.usedCredit += route_data["total_client_cost"]
            locked_client.save(update_fields=["usedCredit"])

            locked_client_company.usedCustomerCredit += route_data["total_client_cost"]
            locked_client_company.save(update_fields=["usedCustomerCredit"])

            # 3. SAVE SMS
            parent_msg = SMSMessage.objects.create(
                destination=destination,
                text=text,
                encoding=encodingType,
                segmentNumber=total_segments,
                characterCount=total_chars,
                status="queued",
                systemId=source_addr,
                smpp=smpp,
                client=locked_client,
                vendor=vendor,
                message_id=unique_msg_id,
                concatenated_reference=concat_ref,
                sendClientDlr=sendClientDlr,
                queued_at=timezone.now(),
            )
            create_message_parts(parent_msg, text)

            # 4. WRITE RECEIPTS
            VendorTransaction.objects.create(
                vendor=vendor,
                message=parent_msg,
                transactionType=TransactionType.DEDUCTION,
                segments=total_segments,
                ratePerSegment=route_data["vendor_cost"],
                amount=route_data["total_vendor_cost"],
                balanceSpent=locked_terminating_company.usedVendorCredit,
                description=f"Routing charge for SMS {unique_msg_id}",
            )

            ClientTransaction.objects.create(
                client=locked_client,
                message=parent_msg,
                transactionType=TransactionType.DEDUCTION,
                segments=total_segments,
                ratePerSegment=route_data["client_cost"],
                amount=route_data["total_client_cost"],
                chargePolicy=locked_client.invoicePolicy,
                currency=(
                    locked_client.company.currency.name
                    if locked_client.company.currency
                    else "USD"
                ),
                balanceSpent=locked_client.usedCredit,
                description=f"Sent SMS {unique_msg_id}",
            )

            DetailedSMSReport.objects.create(
                message=parent_msg,
                text_message_id=unique_msg_id,
                senderId=source_addr,
                text=text,
                part_total=total_segments,
                client=locked_client.smppUsername,
                clientRate=route_data["client_cost"],
                client_charge=route_data["total_client_cost"],
                vendor=vendor.profileName,
                vendorRate=route_data["vendor_cost"],
                vendor_charge=route_data["total_vendor_cost"],
                submitStatus="SUBMITTED",
                operatorMNC=route_data.get("mnc", "Unknown"),
                request_time=parent_msg.createdAt,
                destination=destination,
                countryMCC=route_data.get("country_code", "Unknown"),
            )

        return parent_msg

    # @sync_to_async
    # def perform_actual_deduction(
    #     self, client_obj, route_data, total_segments, sms_message_obj
    # ):
    #     vendor_obj = route_data["vendor"]
    #     # terminatingCompany_obj = route_data["terminatingCompany"]
    #     # clientCompany_obj = client_obj.company

    #     raw_terminating_company = route_data["terminatingCompany"]
    #     raw_client_company = client_obj.company
    #     with transaction.atomic():
    #         # ⚡️ 1. THE PADLOCK: Fetch locked versions of the rows directly from the DB
    #         locked_terminating_company = (
    #             type(raw_terminating_company)
    #             .objects.select_for_update()
    #             .get(id=raw_terminating_company.id)
    #         )
    #         locked_client = Client.objects.select_for_update().get(id=client_obj.id)
    #         locked_client_company = (
    #             type(raw_client_company)
    #             .objects.select_for_update()
    #             .get(id=raw_client_company.id)
    #         )
    #         print("\n" + "=" * 50)
    #         print("💳 CREDIT DEDUCTION TRIGGERED 💳")
    #         print(
    #             f"1. Vendor Company: {locked_terminating_company} -> usedVendorCredit increased by {route_data['total_vendor_cost']}"
    #         )
    #         print(
    #             f"2. Client Account: {locked_client} -> usedCredit increased by {route_data['total_client_cost']}"
    #         )
    #         print(
    #             f"3. Client Parent Company: {locked_client_company} -> usedCustomerCredit increased by {route_data['total_client_cost']}"
    #         )
    #         print("=" * 50 + "\n")
    #         # ---------------------------------------\
    #         # ⚡️ 2. THE MATH: Only update the locked versions of the objects
    #         # 1. Add to Vendor's Used Credit
    #         locked_terminating_company.usedVendorCredit += route_data[
    #             "total_vendor_cost"
    #         ]
    #         locked_terminating_company.save(update_fields=["usedVendorCredit"])
    #         # terminatingCompany_obj.usedVendorCredit += route_data["total_vendor_cost"]
    #         # terminatingCompany_obj.save()

    #         # 2. Add to Client's Used Credit
    #         locked_client.usedCredit += route_data["total_client_cost"]
    #         locked_client.save(update_fields=["usedCredit"])
    #         # client_obj.usedCredit += route_data["total_client_cost"]
    #         # client_obj.save()

    #         # 3. Add to the Global Company's Used Credit
    #         locked_client_company.usedCustomerCredit += route_data["total_client_cost"]
    #         locked_client_company.save(update_fields=["usedCustomerCredit"])
    #         # clientCompany_obj.usedCustomerCredit += route_data["total_client_cost"]
    #         # clientCompany_obj.save()
    #         VendorTransaction.objects.create(
    #             vendor=vendor_obj,
    #             message=sms_message_obj,
    #             transactionType=TransactionType.DEDUCTION,
    #             segments=total_segments,
    #             ratePerSegment=route_data["vendor_cost"],
    #             amount=route_data["total_vendor_cost"],
    #             # balanceSpent=terminatingCompany_obj.usedVendorCredit,
    #             balanceSpent=locked_terminating_company.usedVendorCredit,
    #             description=f"Routing charge for SMS {sms_message_obj.message_id}",
    #         )

    #         # 2. Client Ledger (Uncomment when you add the balance field to Client)

    #         ClientTransaction.objects.create(
    #             # client=client_obj,
    #             client=locked_client,  # Use locked_client for accurate foreign key reference
    #             message=sms_message_obj,
    #             transactionType=TransactionType.DEDUCTION,
    #             segments=total_segments,
    #             ratePerSegment=route_data["client_cost"],
    #             amount=route_data["total_client_cost"],
    #             chargePolicy=locked_client.invoicePolicy,
    #             currency=locked_client.company.currency.name,
    #             # balanceSpent=client_obj.usedCredit,
    #             balanceSpent=locked_client.usedCredit,
    #             description=f"Sent SMS {sms_message_obj.message_id}",
    #         )
    #         DetailedSMSReport.objects.create(
    #             message=sms_message_obj,
    #             text_message_id=sms_message_obj.message_id,
    #             senderId=sms_message_obj.systemId,  # or your source address
    #             text=sms_message_obj.text,
    #             part_total=total_segments,
    #             # client=client_obj.smppUsername,
    #             client=locked_client.smppUsername,
    #             clientRate=route_data["client_cost"],
    #             client_charge=route_data["total_client_cost"],
    #             vendor=vendor_obj.profileName,
    #             vendorRate=route_data["vendor_cost"],
    #             vendor_charge=route_data["total_vendor_cost"],
    #             submitStatus="SUBMITTED",
    #             operatorMNC=route_data.get("mnc", "Unknown"),
    #             request_time=sms_message_obj.createdAt,
    #             destination=sms_message_obj.destination,
    #             countryMCC=route_data.get("country_code", "Unknown"),
    #         )

    #     logger.info(f"Ledger updated for Msg {sms_message_obj.message_id}")

    async def save_to_buffer(
        self, system_id, destination, ref_num, total_parts, part_num, text_chunk
    ):
        """Saves chunks to server RAM at lightning speed."""
        key = f"smpp:buffer:{system_id}:{destination}:{ref_num}"

        # Use a pipeline to send multiple commands to Redis in a single atomic transaction
        async with self.redis_client.pipeline(transaction=True) as pipe:
            pipe.hset(key, f"part_{part_num}", text_chunk)
            pipe.hset(key, "total_parts", total_parts)
            # ⚡️ 5-MINUTE AUTO KILL SWITCH (Solves Frankenstein Collisions!)
            pipe.expire(key, 300)
            await pipe.execute()

    async def get_buffered_parts(self, system_id, destination, ref_num):
        """Fetches and sorts the chunks from RAM."""
        key = f"smpp:buffer:{system_id}:{destination}:{ref_num}"
        data = await self.redis_client.hgetall(key)

        if not data:
            return []

        # Extract only the parts and sort them
        parts = []
        for field, value in data.items():
            if field.startswith("part_"):
                p_num = int(field.split("_")[1])
                parts.append((p_num, value))

        parts.sort(
            key=lambda x: x[0]
        )  # Sort by part_num to ensure the sentence is in order!

        # Create a tiny mock object so we don't have to change your Reassembler code!
        class BufferedPart:
            def __init__(self, text):
                self.text_chunk = text

        return [BufferedPart(text) for _, text in parts]

    async def clear_buffer(self, system_id, destination, ref_num):
        """Wipes the chunks from RAM once stitched."""
        key = f"smpp:buffer:{system_id}:{destination}:{ref_num}"
        await self.redis_client.delete(key)

    # @sync_to_async
    # def save_to_buffer(
    #     self, system_id, destination, ref_num, total_parts, part_num, text_chunk
    # ):
    #     from squadServices.models.smpp.smppSMS import MultipartBuffer

    #     obj, created = MultipartBuffer.objects.get_or_create(
    #         system_id=system_id,
    #         destination=destination,
    #         ref_num=ref_num,
    #         part_num=part_num,
    #         defaults={"total_parts": total_parts, "text_chunk": text_chunk},
    #     )
    #     return obj

    # @sync_to_async
    # def get_buffered_parts(self, system_id, destination, ref_num):
    #     from squadServices.models.smpp.smppSMS import MultipartBuffer

    #     # ⚡️ PROTECT AGAINST 255-LOOP COLLISIONS
    #     # Only look for parts that arrived in the last 5 minutes
    #     time_threshold = timezone.now() - timedelta(minutes=5)
    #     # Fetch all parts and order them by part_num so the sentence is stitched correctly!
    #     return list(
    #         MultipartBuffer.objects.filter(
    #             system_id=system_id,
    #             destination=destination,
    #             ref_num=ref_num,
    #             created_at__gte=time_threshold,
    #         ).order_by("part_num")
    #     )

    # @sync_to_async
    # def clear_buffer(self, system_id, destination, ref_num):
    #     from squadServices.models.smpp.smppSMS import MultipartBuffer

    #     MultipartBuffer.objects.filter(
    #         system_id=system_id, destination=destination, ref_num=ref_num
    #     ).delete()

    async def handle_submit_sm(self, body, seq_num, writer):
        """
        Parses SUBMIT_SM, reassembles multipart messages, and loops through
        comma-separated destination numbers for routing and billing.
        """
        offset = 0

        # ==========================================
        # 1. PARSE MANDATORY PARAMETERS (HEADER)
        # ==========================================
        service_type, offset = self.read_c_string(body, offset)
        source_addr_ton = body[offset]
        offset += 1
        source_addr_npi = body[offset]
        offset += 1
        source_addr, offset = self.read_c_string(body, offset)

        dest_addr_ton = body[offset]
        offset += 1
        dest_addr_npi = body[offset]
        offset += 1
        raw_destination_addr, offset = self.read_c_string(body, offset)
        print(f"📞 Parsed destination numbers: {raw_destination_addr}")

        # ⚡️ SPLIT COMMA-SEPARATED NUMBERS
        raw_numbers = [n.strip() for n in raw_destination_addr.split(",") if n.strip()]
        print(f"📞 Parsed destination numbers: {raw_numbers}")
        esm_class = body[offset]
        offset += 1
        protocol_id = body[offset]
        offset += 1
        priority_flag = body[offset]
        offset += 1
        schedule_delivery_time, offset = self.read_c_string(body, offset)
        validity_period, offset = self.read_c_string(body, offset)
        registered_delivery = body[
            offset
        ]  # this value came for the  client when they send the SUBMIT_SM command. It indicates whether the client wants a DLR for this message or not.
        offset += 1

        # Determine DLR requirements
        client_obj = getattr(writer, "client_obj", None)
        client_wants_dlr = (
            registered_delivery == 1
        )  # compare with 1 because in SMPP, a value of 1 means "Yes, I want a DLR", while 0 means "No, I don't want a DLR".
        client_allowed_dlr = (
            getattr(client_obj, "enableDlr", False) if client_obj else False
        )
        final_send_dlr_decision = client_wants_dlr and client_allowed_dlr

        replace_if_present_flag = body[offset]
        offset += 1
        data_coding = body[offset]
        offset += 1
        sm_default_msg_id = body[offset]
        offset += 1
        sm_length = body[offset]
        offset += 1

        # Extract Raw Message Bytes
        raw_short_message = body[offset : offset + sm_length]
        offset += sm_length

        # ==========================================
        # 2. PARSE TLV (OPTIONAL PARAMETERS)
        # ==========================================
        sar_ref_num = None
        sar_total_parts = None
        sar_part_num = None
        # --- UPGRADED TLV PARSING LOOP (Catches SAR) ---
        while offset < len(body):
            if len(body) - offset < 4:
                logger.warning("Rejected: Malformed TLV structure.")
                await self.send_error_with_tlv(writer, seq_num, "INVALID_TLV")
                return None
            # Opening the Box
            tlv_tag, tlv_len = struct.unpack(">HH", body[offset : offset + 4])
            offset += 4
            tlv_value = body[offset : offset + tlv_len]
            offset += tlv_len

            # Normally, SMPP puts the text message in the short_message field.
            # But if the text is massive, clients leave short_message blank and
            # stuff the entire text into this optional TLV tag instead.
            if tlv_tag == 0x0424:
                print("==========", raw_short_message)
                print("📦 Detected TLV 0x0424: This message is using the giant message")
                raw_short_message = tlv_value
                logger.info(
                    f"📦 Found giant message in TLV! Size: {len(raw_short_message)} bytes"
                )
            elif tlv_tag == 0x020C:  # sar_msg_ref_num(SAR Reference Number)
                sar_ref_num = struct.unpack(">H", tlv_value)[0]
            elif tlv_tag == 0x020E:  # sar_total_segments(SAR Total Segments)
                sar_total_parts = struct.unpack(">B", tlv_value)[0]
            elif tlv_tag == 0x020F:  # sar_segment_seqnum(SAR Part Number)
                sar_part_num = struct.unpack(">B", tlv_value)[0]
        # ---------------------------------- if message is coming in as a multi-part message ---------------------------------------------

        # -------------------------------------------------------------------------
        # ⚡️ THE UNIVERSAL REASSEMBLER (UDH & SAR CONSISTENCY CHECK)
        # -------------------------------------------------------------------------
        is_multipart_udh = (
            esm_class & 0x40
        ) > 0  # UDH (User Data Header): The instructions are mixed directly into the text bytes.
        is_multipart_sar = (
            sar_total_parts is not None and sar_total_parts > 1
        )  # SAR (Segmentation and Reassembly): The instructions are attached at the end of the message as extra tags (TLVs).
        ref_num = None
        total_parts = 1
        part_num = 1
        is_multipart = False

        if is_multipart_udh:
            # 1. Extract UDH
            udh_length = raw_short_message[0]
            udh_bytes = raw_short_message[: udh_length + 1]
            raw_short_message = raw_short_message[udh_length + 1 :]

            if udh_length == 5 and udh_bytes[1] == 0x00:  # 8-bit ref
                ref_num = udh_bytes[3]
                total_parts = udh_bytes[4]
                part_num = udh_bytes[5]
            elif udh_length == 6 and udh_bytes[1] == 0x08:  # 16-bit ref
                ref_num = struct.unpack(">H", udh_bytes[3:5])[0]
                total_parts = udh_bytes[5]
                part_num = udh_bytes[6]
            if total_parts == 0 or part_num == 0 or part_num > total_parts:
                logger.warning(
                    f"Rejected: Invalid UDH (Part {part_num} of {total_parts})"
                )
                await self.send_error_with_tlv(writer, seq_num, "INVALID_UDH")
                return None

            # UDH / SAR Conflict Guard
            # Some poorly programmed clients will accidentally send both UDH and SAR instructions,
            # and sometimes they contradict each other (e.g., UDH says "this is a 3-part message",
            # but SAR says "this is a 5-part message").
            if is_multipart_sar and (
                sar_total_parts != total_parts or sar_part_num != part_num
            ):
                logger.warning(
                    f"Rejected: Client sent conflicting UDH and SAR instructions."
                )
                await self.send_error_with_tlv(
                    writer, seq_num, "Protocol Error: UDH and SAR mismatch."
                )
                return None
            is_multipart = True
        elif is_multipart_sar:
            # 2. Use SAR if UDH isn't present
            ref_num = sar_ref_num
            total_parts = sar_total_parts
            part_num = sar_part_num
            is_multipart = True

        # Handle Multipart Buffering
        if is_multipart:
            # Note: We use the raw_destination_addr as the key to group the parts
            # Decode the text
            if data_coding == 8:
                chunk_text = raw_short_message.decode(
                    "utf-16-be", errors="ignore"
                ).replace("\x00", "")
            else:
                chunk_text = raw_short_message.decode("utf-8", errors="ignore").replace(
                    "\x00", ""
                )

            # 2. Park it in the Waiting Room
            await self.save_to_buffer(
                client_obj.smppUsername,
                raw_destination_addr,
                ref_num,
                total_parts,
                part_num,
                chunk_text,
            )
            print(
                f"📦 Parked Part {part_num} of {total_parts} in Waiting Room (Ref: {ref_num})"
            )

            # 3. Check if we have all the pieces
            buffered_parts = await self.get_buffered_parts(
                client_obj.smppUsername, raw_destination_addr, ref_num
            )

            if len(buffered_parts) < total_parts:
                # Still waiting for parts. Return a temp ID and exit early.
                temp_msg_id = await self.generate_message_id()
                resp_body = temp_msg_id.encode("ascii") + b"\0"
                await self.send_pdu(
                    writer, CMD_SUBMIT_SM_RESP, ESME_ROK, seq_num, resp_body
                )
                return temp_msg_id

            # 🎉 GRAND FINALE: ALL PARTS HAVE ARRIVED!
            print(f"✅ All {total_parts} parts received! Stitching message together...")

            # 4. Clean out the waiting room
            await self.clear_buffer(
                client_obj.smppUsername, raw_destination_addr, ref_num
            )
            short_message = "".join([p.text_chunk for p in buffered_parts])
            is_multipart = False  # Turn this off so it behaves like a normal message
            ref_num = None  # Wipe the client's reference number!

        else:
            # If it's a normal, single-part message, handle it normally
            if data_coding == 8:
                short_message = raw_short_message.decode(
                    "utf-16-be", errors="ignore"
                ).replace("\x00", "")
            else:
                short_message = raw_short_message.decode(
                    "utf-8", errors="ignore"
                ).replace("\x00", "")

        # ==========================================
        # 4. PRE-FLIGHT CHECKS & GUARDS
        # ==========================================
        if not short_message.strip():
            account_name = client_obj.smppUsername if client_obj else "UnknownClient"
            logger.warning(f"Rejected: Empty message payload from {account_name}")
            await self.send_error_with_tlv(
                writer, seq_num, "Message text cannot be empty."
            )
            return None

        # ⚡️ GUARD 2: Sender ID Length
        if len(source_addr) > 15:
            logger.warning(f"Rejected: Sender ID '{source_addr}' too long.")
            await self.send_error_with_tlv(
                writer, seq_num, "Invalid Sender ID: Exceeds 15 chars."
            )
            return None

        encoding_type = self.detect_encoding(short_message)
        total_segments, total_chars = self.calculate_segments(
            short_message, encoding_type
        )
        # ------------------------------------------------------------------
        # ⚡️ GUARD 3: Segment Count Limit (Protect against massive messages)
        # ------------------------------------------------------------------
        # Check if the client has a specific limit in the DB, otherwise default to a safe 10 parts
        # MAX_ALLOWED_SEGMENTS = getattr(client_obj, "maxSegments", 10)
        # since i dont have maxsegment in clinet so i put 10 as default
        MAX_ALLOWED_SEGMENTS = 10
        if total_segments > MAX_ALLOWED_SEGMENTS:
            logger.warning(
                f"Rejected: Message from {client_obj.smppUsername} exceeds segment limit "
                f"({total_segments} parts > {MAX_ALLOWED_SEGMENTS} allowed)."
            )
            await self.send_error_with_tlv(
                writer,
                seq_num,
                f"Message too long. Max segments allowed: {MAX_ALLOWED_SEGMENTS}.",
            )
            return None

        final_concat_ref = secrets.randbelow(256) if total_segments > 1 else None

        # ==========================================
        # 5. THE BULK ROUTING & BILLING LOOP
        # ==========================================
        processed_ids = []
        print("-----------", raw_numbers)

        for current_raw_num in raw_numbers:
            # 1. Clean the specific number
            validated_number = clean_phone_number(current_raw_num)
            if not validated_number:
                logger.warning(f"Skipping invalid bulk number: {current_raw_num}")
                continue
            unique_msg_id = await self.generate_message_id()

            destination_addr = validated_number.replace("+", "")

            # 2. Find Route and Check Cost Constraints
            route_data, routing_error = await self.get_route_and_potential_cost(
                client_obj, destination_addr, total_segments
            )

            if routing_error:
                logger.warning(
                    f"Routing/Billing Failed for {destination_addr}: {routing_error}"
                )
                # ⚡️ NEW: Save it to the DB as FAILED. Do not bill the user.
                await self.save_failed_routing_attempt(
                    client_obj,
                    destination_addr,
                    short_message,
                    encoding_type,
                    total_segments,
                    total_chars,
                    source_addr,
                    unique_msg_id,
                    routing_error,
                    final_send_dlr_decision,
                )
                # We still append the ID so the client gets a "success" response
                # (meaning "we accepted your request, but it failed immediately")
                processed_ids.append(unique_msg_id)
                continue

            # 3. Process Valid Message

            try:
                await self.save_and_bill_sms_transaction(
                    client_obj,
                    route_data,
                    destination_addr,
                    short_message,
                    encoding_type,
                    total_segments,
                    total_chars,
                    source_addr,
                    route_data["smpp"],
                    route_data["vendor"],
                    unique_msg_id,
                    final_concat_ref,
                    final_send_dlr_decision,
                )
                processed_ids.append(unique_msg_id)
                logger.info(f"Queued SMS to {destination_addr} | ID: {unique_msg_id}")
            except Exception as e:
                logger.error(
                    f"Failed to process SMS/Billing for {destination_addr}: {e}"
                )

        # ==========================================
        # 6. FINAL CLIENT RESPONSE
        # ==========================================
        if processed_ids:
            # Send back the ID of the last successfully processed message
            last_msg_id = processed_ids[-1]
            resp_body = last_msg_id.encode("ascii") + b"\0"
            await self.send_pdu(
                writer, CMD_SUBMIT_SM_RESP, ESME_ROK, seq_num, resp_body
            )
            return last_msg_id
        else:
            # If the loop finished but 0 numbers were valid/routed, reject the packet
            logger.warning(
                f"Bulk SMS rejected. No valid or routable numbers found in: {raw_destination_addr}"
            )
            await self.send_error_with_tlv(
                writer, seq_num, error_msg="Invalid Destination(s) or Route."
            )
            return None

    # @sync_to_async
    # def save_sms(
    #     self,
    #     destination,
    #     text,
    #     encodingType,
    #     total_segments,
    #     total_chars,
    #     system_id,
    #     smpp=None,
    #     client=None,
    #     vendor=None,
    #     unique_msg_id=None,
    #     concat_ref=None,  # <--- NEW: Pass the reference number here
    #     sendClientDlr=False,
    # ):
    #     """
    #     Django ORM is synchronous, so we wrap it in sync_to_async
    #     """
    #     parent_msg = SMSMessage.objects.create(
    #         destination=destination,
    #         text=text,
    #         encoding=encodingType,
    #         segmentNumber=total_segments,
    #         characterCount=total_chars,
    #         status="queued",  # It reached our server
    #         systemId=system_id,
    #         smpp=smpp,
    #         client=client,
    #         vendor=vendor,
    #         message_id=unique_msg_id,
    #         concatenated_reference=concat_ref,
    #         sendClientDlr=sendClientDlr,
    #         queued_at=timezone.now(),
    #         # external_id=uuid.uuid4(),
    #     )
    #     create_message_parts(parent_msg, text)
    #     return parent_msg

    # TLV = Type-Length-Value
    async def send_error_with_tlv(self, writer, seq, error_msg="Low Balance"):
        """Bypasses strict SMPP rules by faking a success to deliver the text."""
        cmd_id = CMD_SUBMIT_SM_RESP  # submit_sm_resp
        print("=========send_error_with_tlv==========cmd_id:", cmd_id)

        # The server pretends the message was a Success (Status 0), but hides the real error text inside the mandatory message_id field.
        # ⚡️ THE HACK: Force Status 0 so the library doesn't delete our text!
        status = 0x00

        # Add 'ERR:' so the client knows this is actually a rejection
        safe_msg = f"ERR:{error_msg}"[:64].encode("ascii", errors="ignore") + b"\0"
        # Construct the header and send the packet
        length_header = 16 + len(safe_msg)
        header = struct.pack(">IIII", length_header, cmd_id, status, seq)

        writer.write(header + safe_msg)
        await writer.drain()

    async def send_bind_error_with_tlv(
        self, writer, cmd_id, status, seq, error_msg="Bind Failed"
    ):
        print(f"===================Sending BIND error (Status {status}): {error_msg}")
        print("===========send_bind_error_with_tlv========cmd_id:", cmd_id)
        # 1. Bind responses must contain the system_id.
        # Since the login failed, we just send an empty string (a single null byte).
        body_system_id = b"\0"

        # 2. Construct Header and Send
        # NO TLVs! We bypass the library bug entirely.
        length_header = 16 + len(body_system_id)
        header = struct.pack(">IIII", length_header, cmd_id | 0x80000000, status, seq)

        writer.write(header + body_system_id)
        await writer.drain()

    # send_pdu is the only way your server can send a reply back to the client.
    async def send_pdu(self, writer, cmd_id, status, seq, body):
        """Constructs and writes the SMPP PDU"""
        length = 16 + len(body)
        header = struct.pack(">IIII", length, cmd_id, status, seq)
        writer.write(header + body)
        await writer.drain()

    def read_c_string(self, data, offset):
        """Helper to read C-Style null-terminated strings correctly"""
        # Slice from the current offset to the end
        fragment = data[offset:]

        # Find the first null byte in this fragment
        end_idx = fragment.find(b"\0")

        if end_idx == -1:
            # If no null byte found, take the whole remaining data
            return fragment.decode("ascii", errors="ignore"), len(data)

        # Extract the string, decode it, and move the offset past the null byte
        result = fragment[:end_idx].decode("ascii", errors="ignore")
        return result, offset + end_idx + 1

    def extract_c_string(self, data, offset):
        val, _ = self.read_c_string(data, offset)
        return val

    @sync_to_async
    def get_pending_dlrs(self):
        """Fetches messages from the DB that are finished but haven't sent a DLR back to the client yet."""
        return list(
            # WE ADDED .select_related('client') HERE so we can access the username!
            SMSMessage.objects.select_related("client")
            .prefetch_related("dlrevent_set")  # connect the dlrEvent to the smsMessage
            .filter(
                sendClientDlr=True,
                clientDlrPushed=False,
                status__in=["delivered", "failed"],
            )[:50]
        )

    @sync_to_async
    def mark_dlr_pushed(self, msg_obj):
        """Marks the message so we don't send the same receipt twice."""
        msg_obj.clientDlrPushed = True
        msg_obj.save(update_fields=["clientDlrPushed"])

    async def dlr_dispatcher_loop(self):
        """Runs constantly in the background looking for receipts to send."""
        await asyncio.sleep(5)  # Let the server fully start up first

        while True:
            try:
                await self.reap_stale_messages()
                pending_msgs = await self.get_pending_dlrs()
                tasks = []  # ⚡️ Create a list of tasks

                for msg in pending_msgs:
                    # ---> THE FIX <---
                    # Find the connection using the Client's login username ("yukesh"),
                    # NOT the SMS Sender ID ("SQUAD")!
                    target_username = msg.client.smppUsername if msg.client else None

                    if target_username and target_username in self.active_clients:
                        writer = self.active_clients[target_username]

                        # Create a quick async wrapper
                        async def push_dlr(w, m, username):
                            await self.send_deliver_sm(w, m)
                            await self.mark_dlr_pushed(m)

                        tasks.append(
                            asyncio.create_task(push_dlr(writer, msg, target_username))
                        )
                # ⚡️ Blast them all out concurrently!
                if tasks:
                    await asyncio.gather(*tasks)

            except Exception as e:
                logger.error(f"DLR Dispatcher Error: {e}")

            # Wait 2 seconds before checking the database again
            await asyncio.sleep(2)

    async def send_deliver_sm(self, writer, msg_obj):
        """Formats and sends the exact SMPP bytes for a Delivery Receipt."""

        # grabs the most recent DLR event for this message to get the real status code (instead of just "delivered" or "failed" from the SMSMessage table)
        latest_event = await sync_to_async(
            lambda: msg_obj.dlrevent_set.order_by("-received_at").first()
        )()
        real_err = (
            latest_event.status_code
            if latest_event and latest_event.status_code
            else "000"
        )

        # 1. Get the total parts from the parent message
        total_parts = int(msg_obj.segmentNumber) if msg_obj.segmentNumber else 1

        # 2. Count how many parts are actually marked 'DELIVERED' in the database
        # Use sync_to_async because this is a new database query
        delivered_parts_count = await sync_to_async(
            lambda: msg_obj.parts.filter(submit_status="DELIVERED").count()
        )()
        # 1. Format Dates (YYMMDDHHMMSS)
        submit_date = (
            msg_obj.queued_at.strftime("%y%m%d%H%M%S")
            if msg_obj.queued_at
            else timezone.now().strftime("%y%m%d%H%M%S")
        )
        done_date = timezone.now().strftime("%y%m%d%H%M%S")

        # 2. Map standard DB status to Telecom Status
        stat_map = {"delivered": "DELIVRD", "failed": "REJECTD"}
        smpp_stat = stat_map.get(msg_obj.status, "UNKNOWN")

        # 3. Create the DLR text string

        # ONLY GET 20 LETTER OF THE TEXT
        short_text = msg_obj.text[:20] if msg_obj.text else ""

        # If your message has 1 part: it becomes 001.

        # If your message has 2 parts: it becomes 002.

        # If your message has 10 parts: it becomes 010.
        # The :03 part inside the curly braces tells
        # Python: "I want this number to be at least 3 characters wide
        dlr_string = (
            f"id:{msg_obj.message_id} "
            f"sub:{total_parts:03} "  # submitted parts (total parts in the message)
            f"dlvrd:{delivered_parts_count:03} "
            f"submit date:{submit_date} "
            f"done date:{done_date} "
            f"stat:{smpp_stat} "
            f"err:{real_err} "  # <--- Now using your DLREvent table!
            f"text:{short_text}"
        )
        # We send back the exact message_id we generated for them in SUBMIT_SM_RESP
        # dlr_string = f"id:{msg_obj.message_id} sub:001 dlvrd:001 submit date:{submit_date} done date:{done_date} stat:{smpp_stat} err:000 text:{short_text}"
        dlr_bytes = dlr_string.encode("utf-8", errors="ignore")

        # 4. Pack the SMPP Body
        service_type = b"\0"
        source_addr_ton = b"\x01"
        source_addr_npi = b"\x01"
        source_addr = msg_obj.destination.encode("ascii") + b"\0"

        dest_addr_ton = b"\x01"
        dest_addr_npi = b"\x01"
        dest_addr = msg_obj.systemId.encode("ascii") + b"\0"

        esm_class = b"\x04"  # 0x04 tells the client "This is a Receipt!"
        protocol_id = b"\x00"
        priority_flag = b"\x00"
        schedule_delivery_time = b"\0"
        validity_period = b"\0"
        registered_delivery = b"\x00"
        replace_if_present_flag = b"\x00"
        data_coding = b"\x00"
        sm_default_msg_id = b"\x00"
        sm_length = struct.pack(">B", len(dlr_bytes))

        body = (
            service_type
            + source_addr_ton
            + source_addr_npi
            + source_addr
            + dest_addr_ton
            + dest_addr_npi
            + dest_addr
            + esm_class
            + protocol_id
            + priority_flag
            + schedule_delivery_time
            + validity_period
            + registered_delivery
            + replace_if_present_flag
            + data_coding
            + sm_default_msg_id
            + sm_length
            + dlr_bytes
        )

        # 5. Send it (0x00000005 is CMD_DELIVER_SM)
        seq_num = secrets.randbelow(0x7FFFFFFF)
        await self.send_pdu(writer, 0x00000005, 0x00000000, seq_num, body)
