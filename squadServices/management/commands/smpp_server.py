# myapp/management/commands/run_smpp_server.py
from ast import If
import asyncio
from csv import writer
import math
import struct
import logging
from django.core.management.base import BaseCommand
from asgiref.sync import sync_to_async
from django.utils import timezone
from squadServices.helper.checkNumber import clean_phone_number
from squadServices.helper.routeAndCostHelper import get_route_and_cost
from squadServices.helper.smsSplitter import create_message_parts
from squadServices.models.clientModel.client import Client, IpWhitelist
from squadServices.models.connectivityModel.smpp import SMPP
import secrets
from squadServices.models.connectivityModel.verdor import Vendor
from squadServices.models.country import Country
from squadServices.models.detailedReport.detailedReport import DetailedSMSReport
from squadServices.models.operators.operators import Operators
from squadServices.models.routeManager.customRoute import CustomRoute
from squadServices.models.smpp.smppSMS import SMSMessage
import re
from django.db import transaction

from squadServices.models.transaction.transaction import (
    ClientTransaction,
    TransactionType,
    VendorTransaction,
)
import uuid

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


class Command(BaseCommand):
    help = "Runs a lightweight SMPP Server to receive SMS"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.active_clients = {}  # Dictionary to hold open TCP connections

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

    def handle(self, *args, **kwargs):
        self.stdout.write(f"Starting SMPP Server on {HOST}:{PORT}...")
        try:
            asyncio.run(self.run_server())
        except KeyboardInterrupt:
            self.stdout.write("Server stopped.")

    # Once the server is running, it just waits.
    # The moment an external client (like another SMPP server or SMS gateway) connects to your port

    async def run_server(self):
        server = await asyncio.start_server(self.handle_client, HOST, PORT)
        # --- 2. START THE BACKGROUND LOOP HERE ---
        asyncio.create_task(self.dlr_dispatcher_loop())
        async with server:
            await server.serve_forever()

    async def handle_client(self, reader, writer):
        addr = writer.get_extra_info("peername")
        client_ip = addr[0]
        logger.info(f"New connection from {addr}")
        # --- 3. TRACK THE SYSTEM ID ---
        system_id_logged_in = None
        # ------------------------------
        try:
            while True:
                # 1. Read SMPP Header
                header_data = await reader.read(16)
                if not header_data or len(header_data) < 16:
                    break

                cmd_len, cmd_id, cmd_status, seq_num = struct.unpack(
                    ">IIII", header_data
                )

                # 2. Read Body
                body_len = cmd_len - 16
                body_data = await reader.read(body_len) if body_len > 0 else b""

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
                        self.active_clients[system_id] = writer
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
            writer.close()
            await writer.wait_closed()

    @sync_to_async
    def get_route_and_potential_cost(
        self, client_obj, destination_number, total_segments
    ):

        # --- 1. DYNAMIC COUNTRY LOOKUP ---
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
        print(
            "========================destination_country===========",
            destination_country,
        )
        print(
            "==================destination_number=================", destination_number
        )

        # --- 2. CALL THE ROUTING ENGINE (No Operator Needed!) ---
        route_data, error = get_route_and_cost(client_obj, destination_country)

        if error:
            return None, error

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

    @sync_to_async
    def perform_actual_deduction(
        self, client_obj, route_data, total_segments, sms_message_obj
    ):
        vendor_obj = route_data["vendor"]
        # terminatingCompany_obj = route_data["terminatingCompany"]
        # clientCompany_obj = client_obj.company

        raw_terminating_company = route_data["terminatingCompany"]
        raw_client_company = client_obj.company
        with transaction.atomic():
            # ⚡️ 1. THE PADLOCK: Fetch locked versions of the rows directly from the DB
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
            print("\n" + "=" * 50)
            print("💳 CREDIT DEDUCTION TRIGGERED 💳")
            print(
                f"1. Vendor Company: {locked_terminating_company} -> usedVendorCredit increased by {route_data['total_vendor_cost']}"
            )
            print(
                f"2. Client Account: {locked_client} -> usedCredit increased by {route_data['total_client_cost']}"
            )
            print(
                f"3. Client Parent Company: {locked_client_company} -> usedCustomerCredit increased by {route_data['total_client_cost']}"
            )
            print("=" * 50 + "\n")
            # ---------------------------------------\
            # ⚡️ 2. THE MATH: Only update the locked versions of the objects
            # 1. Add to Vendor's Used Credit
            locked_terminating_company.usedVendorCredit += route_data[
                "total_vendor_cost"
            ]
            locked_terminating_company.save(update_fields=["usedVendorCredit"])
            # terminatingCompany_obj.usedVendorCredit += route_data["total_vendor_cost"]
            # terminatingCompany_obj.save()

            # 2. Add to Client's Used Credit
            locked_client.usedCredit += route_data["total_client_cost"]
            locked_client.save(update_fields=["usedCredit"])
            # client_obj.usedCredit += route_data["total_client_cost"]
            # client_obj.save()

            # 3. Add to the Global Company's Used Credit
            locked_client_company.usedCustomerCredit += route_data["total_client_cost"]
            locked_client_company.save(update_fields=["usedCustomerCredit"])
            # clientCompany_obj.usedCustomerCredit += route_data["total_client_cost"]
            # clientCompany_obj.save()
            VendorTransaction.objects.create(
                vendor=vendor_obj,
                message=sms_message_obj,
                transactionType=TransactionType.DEDUCTION,
                segments=total_segments,
                ratePerSegment=route_data["vendor_cost"],
                amount=route_data["total_vendor_cost"],
                # balanceSpent=terminatingCompany_obj.usedVendorCredit,
                balanceSpent=locked_terminating_company.usedVendorCredit,
                description=f"Routing charge for SMS {sms_message_obj.message_id}",
            )

            # 2. Client Ledger (Uncomment when you add the balance field to Client)

            ClientTransaction.objects.create(
                # client=client_obj,
                client=locked_client,  # Use locked_client for accurate foreign key reference
                message=sms_message_obj,
                transactionType=TransactionType.DEDUCTION,
                segments=total_segments,
                ratePerSegment=route_data["client_cost"],
                amount=route_data["total_client_cost"],
                # balanceSpent=client_obj.usedCredit,
                balanceSpent=locked_client.usedCredit,
                description=f"Sent SMS {sms_message_obj.message_id}",
            )
            DetailedSMSReport.objects.create(
                message=sms_message_obj,
                text_message_id=sms_message_obj.message_id,
                senderId=sms_message_obj.systemId,  # or your source address
                text=sms_message_obj.text,
                part_total=total_segments,
                # client=client_obj.smppUsername,
                client=locked_client.smppUsername,
                clientRate=route_data["client_cost"],
                client_charge=route_data["total_client_cost"],
                vendor=vendor_obj.profileName,
                vendorRate=route_data["vendor_cost"],
                vendor_charge=route_data["total_vendor_cost"],
                submitStatus="SUBMITTED",
                operatorMNC=route_data.get("mnc", "Unknown"),
                request_time=sms_message_obj.createdAt,
                destination=sms_message_obj.destination,
                countryMCC=route_data.get("country_code", "Unknown"),
            )

        logger.info(f"Ledger updated for Msg {sms_message_obj.message_id}")

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
        raw_destination_addr, offset = self.read_c_string(body, offset)
        # It cleans the phone number and detects the encoding (GSM-7).
        validated_number = clean_phone_number(raw_destination_addr)

        # response for bad phone numbers
        if not validated_number:
            logger.warning(
                f"Invalid destination number rejected: {raw_destination_addr}"
            )
            await self.send_error_with_tlv(
                writer, seq_num, error_msg="Invalid Destination Number"
            )
            # await self.send_pdu(writer, CMD_SUBMIT_SM_RESP, 0x0000000B, seq_num, b"")
            # You should probably reject the SMPP message here!
            return None
        destination_addr = validated_number.replace("+", "")
        client_obj = getattr(writer, "client_obj", None)

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
        client_wants_dlr = (
            registered_delivery == 1
        )  # compare with 1 because in SMPP, a value of 1 means "Yes, I want a DLR", while 0 means "No, I don't want a DLR".
        client_allowed_dlr = getattr(client_obj, "enableDlr", False)
        final_send_dlr_decision = client_wants_dlr and client_allowed_dlr
        replace_if_present_flag = body[offset]
        offset += 1
        data_coding = body[offset]
        offset += 1
        sm_default_msg_id = body[offset]
        offset += 1
        sm_length = body[offset]
        offset += 1

        # Extract the raw bytes first
        raw_short_message = body[offset : offset + sm_length]
        print("Raw short message bytes:", raw_short_message)
        # Decode properly based on the Data Coding flag (8 = UCS2/UTF-16)
        if data_coding == 8:
            short_message = raw_short_message.decode("utf-16-be", errors="ignore")
        else:
            short_message = raw_short_message.decode("utf-8", errors="ignore")
        print("Decoded short message:", short_message)

        # Bulletproof Postgres Guard: Strip any stray Null bytes!
        short_message = short_message.replace("\x00", "")

        # short_message = body[offset : offset + sm_length].decode(
        #     "utf-8", errors="ignore"
        # )
        encoding_type = self.detect_encoding(short_message)
        total_segments, total_chars = self.calculate_segments(
            short_message, encoding_type
        )
        if not short_message.strip():
            account_name = client_obj.smppUsername if client_obj else "UnknownClient"
            logger.warning(f"Rejected: Empty message payload from {account_name}")
            await self.send_error_with_tlv(
                writer, seq_num, error_msg="Message text cannot be empty."
            )
            return None

        # ⚡️ GUARD 2: Sender ID Length
        if len(source_addr) > 15:
            logger.warning(f"Rejected: Sender ID '{source_addr}' too long.")
            await self.send_error_with_tlv(
                writer, seq_num, error_msg="Invalid Sender ID: Exceeds 15 chars."
            )
            return None
        route_data, routing_error = await self.get_route_and_potential_cost(
            client_obj, destination_addr, total_segments
        )
        concat_ref = None
        if total_segments > 1:
            # Generate a random 1-byte reference (0-255)
            concat_ref = secrets.randbelow(256)
        # response for routing/billing failures
        if routing_error:
            logger.warning(
                f"Routing/Billing Failed for {destination_addr}: {routing_error}"
            )
            await self.send_error_with_tlv(writer, seq_num, error_msg=routing_error)
            # await self.send_pdu(writer, CMD_SUBMIT_SM_RESP, 0x00000045, seq_num, b"")
            return None  # This will trigger the 0x0000000B rejection in handle_client!
        vendor = route_data["vendor"]
        smpp = route_data["smpp"]
        # Extract SMS Text
        # Generate 36 bit unique message ID
        unique_msg_id = await self.generate_message_id()  # Add 'await'
        logger.info(
            f"Received SMS from {source_addr} to {destination_addr}: {short_message}"
        )
        print(f"Received SMS from {source_addr} to {destination_addr}: {short_message}")

        # Save to Database (Async Wrapper)
        client = getattr(writer, "client_obj", None)
        try:
            saved_msg = await self.save_sms(
                destination_addr,
                short_message,
                encoding_type,
                total_segments,
                total_chars,
                source_addr,
                smpp,
                client_obj,  # client data
                vendor,
                unique_msg_id,
                concat_ref=concat_ref,
                sendClientDlr=final_send_dlr_decision,
            )
            await self.perform_actual_deduction(
                client_obj, route_data, total_segments, saved_msg
            )
            resp_body = unique_msg_id.encode("ascii") + b"\0"
            await self.send_pdu(
                writer, CMD_SUBMIT_SM_RESP, ESME_ROK, seq_num, resp_body
            )
            return unique_msg_id
        except Exception as e:
            logger.error(f"Failed to process SMS/Billing: {e}")
            await self.send_error_with_tlv(
                writer, seq_num, error_msg="Internal Gateway Error. Please retry."
            )
            # await self.send_pdu(writer, CMD_SUBMIT_SM_RESP, 0x00000045, seq_num, b"")
            return None

    @sync_to_async
    def save_sms(
        self,
        destination,
        text,
        encodingType,
        total_segments,
        total_chars,
        system_id,
        smpp=None,
        client=None,
        vendor=None,
        unique_msg_id=None,
        concat_ref=None,  # <--- NEW: Pass the reference number here
        sendClientDlr=False,
    ):
        """
        Django ORM is synchronous, so we wrap it in sync_to_async
        """
        parent_msg = SMSMessage.objects.create(
            destination=destination,
            text=text,
            encoding=encodingType,
            segmentNumber=total_segments,
            characterCount=total_chars,
            status="queued",  # It reached our server
            systemId=system_id,
            smpp=smpp,
            client=client,
            vendor=vendor,
            message_id=unique_msg_id,
            concatenated_reference=concat_ref,
            sendClientDlr=sendClientDlr,
            queued_at=timezone.now(),
            external_id=uuid.uuid4(),
        )
        create_message_parts(parent_msg, text)
        return parent_msg

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
                status__in=["delivered", "failed", "partially_delivered"],
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
                pending_msgs = await self.get_pending_dlrs()

                for msg in pending_msgs:
                    # ---> THE FIX <---
                    # Find the connection using the Client's login username ("yukesh"),
                    # NOT the SMS Sender ID ("SQUAD")!
                    target_username = msg.client.smppUsername if msg.client else None

                    if target_username and target_username in self.active_clients:
                        writer = self.active_clients[target_username]

                        # Push the receipt down the socket!
                        await self.send_deliver_sm(writer, msg)

                        # Mark it as sent in the database
                        await self.mark_dlr_pushed(msg)
                        logger.info(
                            f"Pushed DLR to {target_username} for msg ID: {msg.message_id}"
                        )

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
        stat_map = {
            "delivered": "DELIVRD",
            "failed": "REJECTD",
            "partially_delivered": "DELIVRD",
        }
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
