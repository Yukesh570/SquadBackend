# myapp/management/commands/run_smpp_server.py
import asyncio
from csv import writer
import struct
import logging
from django.core.management.base import BaseCommand
from asgiref.sync import sync_to_async
from squadServices.models.clientModel.client import Client
from squadServices.models.connectivityModel.smpp import SMPP

from squadServices.models.connectivityModel.verdor import Vendor
from squadServices.models.routeManager.customRoute import CustomRoute
from squadServices.models.smpp.smppSMS import SMSMessage

# Configuration
# HOST = "192.168.10.3"
HOST = "0.0.0.0"
PORT = 2775

# SMPP Command IDs
CMD_BIND_RECEIVER = 0x00000001
CMD_BIND_TRANSMITTER = 0x00000002
CMD_BIND_TRANSCEIVER = 0x00000009
CMD_SUBMIT_SM = 0x00000004
CMD_ENQUIRE_LINK = 0x00000015

# Response IDs (Request ID + 0x80000000)
CMD_BIND_RECEIVER_RESP = 0x80000001
CMD_BIND_TRANSMITTER_RESP = 0x80000002
CMD_BIND_TRANSCEIVER_RESP = 0x80000009
CMD_SUBMIT_SM_RESP = 0x80000004
CMD_ENQUIRE_LINK_RESP = 0x80000015
CMD_GENERIC_NACK = 0x80000000

# SMPP Status
ESME_ROK = 0x00000000

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs a lightweight SMPP Server to receive SMS"

    # Get all the smppuser from smpp database
    @sync_to_async
    def authenticate_and_get_route(self, username, password):
        """
        Authenticates the client and finds their assigned vendor via CustomRoute.
        """

        try:
            # 1. Authenticate the Client
            client = Client.objects.filter(
                smppUsername=username, smppPassword=password
            ).first()  # Get the actual object, not just True/False
            print("smpp client:::::::", client)
            if not client:
                return None, None, None

            # 2. Find the CustomRoute for this Client
            # We look for an active route that isn't deleted
            route = (
                CustomRoute.objects.filter(
                    orginatingClient=client, status="ACTIVE", isDeleted=False
                )
                .select_related("terminatingVendor")
                .first()
            )
            print("smpp vendor:::::::", route.terminatingVendor.smpp)

            if route and route.terminatingVendor.smpp.id:
                return client, route.terminatingVendor, route.terminatingVendor.smpp

            return client, None, None  # Client is valid, but no route/vendor found

        except Exception as e:
            logger.error(f"Auth/Route Lookup Error: {e}")
            return None, None, None

    def handle(self, *args, **kwargs):
        self.stdout.write(f"Starting SMPP Server on {HOST}:{PORT}...")
        try:
            asyncio.run(self.run_server())
        except KeyboardInterrupt:
            self.stdout.write("Server stopped.")

    async def run_server(self):
        server = await asyncio.start_server(self.handle_client, HOST, PORT)
        async with server:
            await server.serve_forever()

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info("peername")
        logger.info(f"New connection from {addr}")
        print(f"DEBUG BODY HEX: {body_data.hex()}")
        try:
            while True:
                # 1. Read SMPP Header (16 bytes)
                header_data = await reader.read(16)
                if not header_data or len(header_data) < 16:
                    break

                # Unpack Header: Length, Command ID, Status, Sequence
                cmd_len, cmd_id, cmd_status, seq_num = struct.unpack(
                    ">IIII", header_data
                )

                # 2. Read Body (Length - 16 bytes header)
                body_len = cmd_len - 16
                body_data = await reader.read(body_len) if body_len > 0 else b""

                # 3. Process Command
                resp_id = cmd_id | 0x80000000  # Generic response ID logic
                resp_body = b""

                if cmd_id in [
                    CMD_BIND_RECEIVER,
                    CMD_BIND_TRANSMITTER,
                    CMD_BIND_TRANSCEIVER,
                ]:
                    system_id, offset = self.read_c_string(body_data, 0)
                    password, offset = self.read_c_string(body_data, offset)
                    print("credential", system_id, password)

                    client_obj, vendor_obj, smpp_obj = (
                        await self.authenticate_and_get_route(system_id, password)
                    )
                    if client_obj:
                        # SUCCESS: Mark this connection as authenticated
                        writer.is_authenticated = True
                        writer.client_obj = client_obj  # Store for logging later
                        writer.vendor_obj = vendor_obj
                        writer.smpp_obj = smpp_obj
                        logger.info(f"Auth Success: {system_id}")
                        resp_body = system_id.encode("ascii") + b"\0"
                        await self.send_pdu(
                            writer, resp_id, ESME_ROK, seq_num, resp_body
                        )
                    else:
                        # FAILURE: Mark as NOT authenticated
                        writer.is_authenticated = False

                        logger.warning(f"Auth Failed: {system_id}")
                        await self.send_pdu(writer, resp_id, 0x0000000F, seq_num, b"")

                        # PRO-TIP: Close the connection immediately on bad login
                        writer.close()
                        return
                elif cmd_id == CMD_SUBMIT_SM:
                    # --- THE GUARD ---
                    if not getattr(writer, "is_authenticated", False):
                        logger.warning("Unauthenticated SUBMIT_SM attempt blocked.")
                        # Send Error: ESME_RINVBNDSTS (Incorrect Bind Status) = 0x00000004
                        await self.send_pdu(
                            writer, CMD_SUBMIT_SM_RESP, 0x00000004, seq_num, b""
                        )
                        return
                    # -----------------

                    # Handle the SMS only if they are logged in
                    await self.handle_submit_sm(body_data, seq_num, writer)
                    msg_id = f"ID{seq_num}".encode("ascii") + b"\0"
                    await self.send_pdu(
                        writer, CMD_SUBMIT_SM_RESP, ESME_ROK, seq_num, msg_id
                    )

                elif cmd_id == CMD_ENQUIRE_LINK:
                    # Keep-alive
                    await self.send_pdu(
                        writer, CMD_ENQUIRE_LINK_RESP, ESME_ROK, seq_num, b""
                    )

                else:
                    # Unknown command, send Generic NACK
                    await self.send_pdu(
                        writer, CMD_GENERIC_NACK, 0x00000003, seq_num, b""
                    )

        except Exception as e:
            logger.error(f"Error handling client: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def handle_submit_sm(self, body, seq_num, writer):
        """
        Parses the SUBMIT_SM body and saves to Django DB.
        """
        offset = 0

        # Parse mandatory parameters
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
        destination_addr, offset = self.read_c_string(body, offset)

        esm_class = body[offset]
        offset += 1
        protocol_id = body[offset]
        offset += 1
        priority_flag = body[offset]
        offset += 1
        schedule_delivery_time, offset = self.read_c_string(body, offset)
        validity_period, offset = self.read_c_string(body, offset)
        registered_delivery = body[offset]
        offset += 1
        replace_if_present_flag = body[offset]
        offset += 1
        data_coding = body[offset]
        offset += 1
        sm_default_msg_id = body[offset]
        offset += 1
        sm_length = body[offset]
        offset += 1

        # Extract SMS Text
        short_message = body[offset : offset + sm_length].decode(
            "utf-8", errors="ignore"
        )

        logger.info(
            f"Received SMS from {source_addr} to {destination_addr}: {short_message}"
        )
        print(f"Received SMS from {source_addr} to {destination_addr}: {short_message}")

        # Save to Database (Async Wrapper)
        client = getattr(writer, "client_obj", None)
        vendor = getattr(writer, "vendor_obj", None)
        smpp = getattr(writer, "smpp_obj", None)
        await self.save_sms(
            destination_addr, short_message, source_addr, smpp, client, vendor
        )

    @sync_to_async
    def save_sms(
        self, destination, text, system_id, smpp=None, client=None, vendor=None
    ):
        """
        Django ORM is synchronous, so we wrap it in sync_to_async
        """
        print("smpp!!!!!!!!=====!!!!!!!", smpp)
        SMSMessage.objects.create(
            destination=destination,
            text=text,
            status="queued",  # It reached our server
            systemId=system_id,
            smpp=smpp,
            client=client,
            vendor=vendor,
            message_id=f"Internal",
        )

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
