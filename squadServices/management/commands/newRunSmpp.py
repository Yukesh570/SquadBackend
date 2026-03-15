import time
import logging
import socket
import re
import smpplib.client
import smpplib.consts
from django.core.management.base import BaseCommand
from squadServices.models.smpp.smppSMS import SMSMessage, SMSMessagePart
from django.utils import timezone
import smpplib.exceptions

# Turn on X-Ray Vision for raw network packets
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("smpplib").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs a Multi-Gateway SMPP Client Manager (UDH Part Architecture)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sessions = {}
        # This maps the SMPP Sequence Number to our Database PART ID
        self.sequence_to_part_id = {}

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Multi-Gateway SMPP Manager..."))

        while True:
            try:
                # STEP 1: Process Outgoing Queue (NOW PULLING PARTS, NOT PARENT MESSAGES)
                # We use select_related to easily access the parent message's config
                queued_parts = (
                    SMSMessagePart.objects.filter(submit_status="QUEUED")
                    .select_related("message", "message__smpp")
                    .order_by("message__createdAt", "part_no")[
                        :10
                    ]  # worker constantly polls the database for up to 10 SMSMessagePart rows where submit_status="QUEUED"
                )

                for part in queued_parts:
                    parent_msg = part.message

                    if not parent_msg.smpp:
                        part.submit_status = "FAILED"
                        part.save()
                        continue

                    smpp_id = parent_msg.smpp.id

                    # Connection Management
                    if smpp_id not in self.sessions:
                        last_attempt = getattr(self, f"last_attempt_{smpp_id}", 0)
                        if time.time() - last_attempt < 10:
                            continue

                        setattr(self, f"last_attempt_{smpp_id}", time.time())
                        self.stdout.write(
                            f"Connecting to {parent_msg.smpp.smppHost}..."
                        )
                        client = self.connect_to_gateway(parent_msg.smpp)

                        if client:
                            self.sessions[smpp_id] = client
                        else:
                            continue

                    # Send the specific part
                    client = self.sessions[smpp_id]
                    self.send_single_part(client, part, parent_msg.smpp)

                # STEP 2: Listen for DLRs on all active sessions
                for smpp_id, client in list(self.sessions.items()):
                    try:
                        client.read_once()
                    except socket.timeout:
                        pass
                    except (smpplib.exceptions.ConnectionError, OSError):
                        self.stdout.write(
                            self.style.ERROR(f"Lost connection to Gateway {smpp_id}")
                        )
                        del self.sessions[smpp_id]

                if not queued_parts:
                    time.sleep(1)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Global Loop Error: {e}")
                time.sleep(2)

    # This method establishes a connection to the SMPP gateway and binds as per the configuration
    def connect_to_gateway(self, config):
        try:
            client = smpplib.client.Client(config.smppHost, config.smppPort, timeout=1)

            # Register Handlers
            client.set_message_received_handler(
                lambda pdu: self.handle_incoming(pdu, config)
            )
            client.set_message_sent_handler(
                lambda pdu: self.handle_sent_confirmation(pdu)
            )

            client.connect()
            mode = config.bindMode.upper()
            if mode == "TRANSMITTER":
                client.bind_transmitter(
                    system_id=config.systemID, password=config.password
                )
            elif mode == "RECEIVER":
                client.bind_receiver(
                    system_id=config.systemID, password=config.password
                )
            else:
                client.bind_transceiver(
                    system_id=config.systemID, password=config.password
                )

            return client
        except Exception as e:
            logger.error(f"Connect failed: {e}")
            return None

    def send_single_part(self, client, part, config):
        parent_msg = part.message
        part.submit_attempts += 1
        part.last_submit_at = timezone.now()
        part.save(update_fields=["submit_attempts", "last_submit_at"])

        try:
            source = parent_msg.systemId if parent_msg.systemId else config.systemID
            # Ensure text is bytes
            msg_content = part.short_message
            final_msg = (
                bytes(msg_content)
                if isinstance(msg_content, (memoryview, bytes))
                else str(msg_content).encode("utf-8")
            )

            # --- FIX: Generate Sequence BEFORE sending ---
            next_seq = client.next_sequence()
            self.sequence_to_part_id[next_seq] = part.id

            client.send_message(
                source_addr=source,
                destination_addr=parent_msg.destination,
                source_addr_ton=config.sourceTON,
                source_addr_npi=config.sourceNPI,
                dest_addr_ton=config.destTON,
                dest_addr_npi=config.destNPI,
                data_coding=0,  # Try 0 for standard GSM text
                esm_class=part.esm_class,
                short_message=final_msg,
                registered_delivery=True,
                sequence=next_seq,  # Use our pre-generated sequence
            )

            # Wait a tiny bit for the response to be processed by read_once
            time.sleep(0.2)
            try:
                client.read_once()
            except:
                pass

            part.submit_status = "SUBMITTED"
            part.save(update_fields=["submit_status"])

            if parent_msg.status == "queued":
                parent_msg.status = "sent"
                parent_msg.save()

            self.stdout.write(self.style.SUCCESS(f"Processed Msg #{parent_msg.id}"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {e}"))
            part.submit_status = "FAILED"
            part.save()

    def handle_sent_confirmation(self, pdu):
        """When the vendor accepts the msg, they give us their Tracking ID"""
        try:
            print(
                f"\n--- DEBUG: Received Response! Sequence: {pdu.sequence}, Status: {pdu.status} ---"
            )

            # 1. Safely extract the raw ID
            raw_id = getattr(pdu, "message_id", None)
            print(f"--- DEBUG: Raw Vendor ID is: {raw_id} ---")

            if not raw_id:
                print("--- DEBUG: Vendor accepted it, but returned NO ID! ---")
                return

            # 2. Safely decode it whether it is bytes or a regular string
            if isinstance(raw_id, bytes):
                vendor_id = raw_id.decode("ascii", errors="ignore").strip("\x00")
            else:
                vendor_id = str(raw_id).strip("\x00")

            # 3. Match it to our database
            part_id = self.sequence_to_part_id.get(pdu.sequence)

            if part_id:
                # Link the vendor's tracking ID to our PART row
                SMSMessagePart.objects.filter(id=part_id).update(
                    vendor_msg_id=vendor_id
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Linked Part #{part_id} to Vendor ID: {vendor_id}"
                    )
                )
                del self.sequence_to_part_id[pdu.sequence]
            else:
                print(
                    f"--- DEBUG: Found sequence {pdu.sequence}, but no matching part ID in dictionary! ---"
                )

        except Exception as e:
            print(f"--- DEBUG: Error inside handle_sent_confirmation: {e} ---")

    def handle_incoming(self, pdu, config):
        try:
            content = pdu.short_message.decode("utf-8", errors="ignore")
            # Improved Regex to catch IDs like 7c6b98...
            match_id = re.search(r"id:([A-F0-9a-z]+)", content, re.IGNORECASE)
            # Catch REJECTD, DELIVRD, etc.
            match_stat = re.search(r"stat:([A-Z]+)", content, re.IGNORECASE)

            if match_id and match_stat:
                v_id = match_id.group(1)
                v_stat = match_stat.group(1)

                status_map = {
                    "DELIVRD": "DELIVERED",
                    "REJECTD": "FAILED",
                    "UNDELIV": "FAILED",
                    "EXPIRED": "FAILED",
                }
                new_status = status_map.get(v_stat, "SUBMITTED")

                # Update using the Vendor ID
                updated = SMSMessagePart.objects.filter(vendor_msg_id=v_id).update(
                    submit_status=new_status
                )
                if updated:
                    self.stdout.write(
                        self.style.SUCCESS(f"DLR: {v_id} is now {new_status}")
                    )
        except Exception as e:
            logger.error(f"DLR Error: {e}")
