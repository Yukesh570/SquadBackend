from datetime import timedelta
import time
import logging
import socket
import re
import smpplib.client
import smpplib.consts
from django.core.management.base import BaseCommand
from squadServices.models.smpp.smppSMS import (
    DLREvent,
    MessageAttempt,
    SMSMessage,
    SMSMessagePart,
)
from django.utils import timezone
import smpplib.exceptions
from squadServices.models.detailedReport.detailedReport import (
    DetailedSMSReport,
)
from django.utils import timezone

# Turn on X-Ray Vision for raw network packets
# logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
# logging.getLogger("smpplib").setLevel(logging.DEBUG)
logging.getLogger("smpplib").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs a Multi-Gateway SMPP Client Manager (UDH Part Architecture)"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sessions = {}
        # This maps the SMPP Sequence Number to our Database PART ID
        self.sequence_to_part_id = {}
        self.last_sweep_time = 0

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Multi-Gateway SMPP Manager..."))

        while True:
            try:
                # ---> 1. Professionally clean up unresponsive vendor messages first
                # ONLY run the sweeper once every 60 seconds to save database performance
                if time.time() - self.last_sweep_time > 60:
                    self.sweep_stale_submissions()
                    self.last_sweep_time = time.time()  # Reset the clock
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
                    if parent_msg.status == "failed":
                        part.submit_status = "FAILED"
                        part.failed_at = timezone.now()
                        part.failure_reason = (
                            "Cancelled: Parent message already failed."
                        )
                        part.save(
                            update_fields=[
                                "submit_status",
                                "failed_at",
                                "failure_reason",
                            ]
                        )
                        continue
                    # ------------------------------------------------
                    if not parent_msg.smpp:
                        part.submit_status = "FAILED"
                        part.save()
                        continue

                    smpp_id = parent_msg.smpp.id
                    # Instead of opening a brand new connection for every single text message
                    # (which would be incredibly slow and get you blocked by the vendor),
                    # this code uses a "Connection Pool" and a "Cooldown Timer."
                    # Connection Management

                    # Think of self.sessions as a dictionary of active phone calls.
                    # If you already have an open line to "RouteMobile" (smpp_id = 1),
                    # it skips this entire block and reuses the open line.
                    if smpp_id not in self.sessions:
                        # If you aren't connected, it checks exactly what time you last tried to connect.
                        last_attempt = getattr(self, f"last_attempt_{smpp_id}", 0)
                        if time.time() - last_attempt < 10:
                            continue

                        setattr(self, f"last_attempt_{smpp_id}", time.time())
                        self.stdout.write(
                            f"Connecting to {parent_msg.smpp.smppHost}..."
                        )
                        client = self.connect_to_gateway(parent_msg.smpp)
                        print("Client after connection attempt:", client)
                        if client:
                            # If the connection succeeds, it saves the active connection object into the dictionary
                            # so the next message in the queue can use it instantly.
                            self.sessions[smpp_id] = client
                        else:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"Connection to Vendor {smpp_id} failed! Marking part as FAILED."
                                )
                            )
                            part.submit_status = "FAILED"
                            part.failed_at = timezone.now()
                            part.failure_reason = (
                                "Vendor Connection Failed (Server Down/Timeout)."
                            )
                            part.save(
                                update_fields=[
                                    "submit_status",
                                    "failed_at",
                                    "failure_reason",
                                ]
                            )

                            # Ensure the parent message also knows it failed!
                            self.update_parent_message_status(parent_msg)
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
            # This opens the raw TCP socket to the vendor's IP address and Port (like dialing a phone number).
            client = smpplib.client.Client(config.smppHost, config.smppPort, timeout=1)

            # Register Handlers
            # If the vendor ever randomly sends us a Delivery Receipt, instantly pass it to my handle_incoming function.

            # this run only after the bind is completed
            client.set_message_received_handler(
                lambda pdu: self.handle_incoming(pdu, config)
            )
            # When the vendor replies 'Yes, I accept this message', pass that response to my handle_sent_confirmation function.
            # this run only after the bind is completed

            client.set_message_sent_handler(
                lambda pdu: self.handle_sent_confirmation(pdu)
            )
            # The Network Connection (Ringing the Phone)
            # This line has nothing to do with SMS yet.
            # This simply tells your server to open a raw TCP/IP network socket to the vendor's IP address and Port.
            # This is you dialing the phone number and hearing the line connect on the other end.
            # You are connected, but no one knows who you are yet.
            client.connect()
            mode = config.bindMode.upper()
            # Once the network line is open, you have to speak the SMPP language to log in. This is called a "Bind".
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

        source = parent_msg.systemId if parent_msg.systemId else config.systemID
        msg_content = part.short_message
        final_msg = (
            bytes(msg_content)
            if isinstance(msg_content, (memoryview, bytes))
            else str(msg_content).encode("utf-8")
        )

        # Generate a unique sequence number for this message and map it to our PART ID
        next_seq = client.next_sequence()
        # Think of this as a notebook where your system temporarily writes down tracking information
        self.sequence_to_part_id[next_seq] = part.id

        # 1. CREATE THE LOG (Record the 'request_payload' here)
        # started_at is automatically added by Django!
        attempt_log = MessageAttempt.objects.create(
            message=parent_msg,
            segment=part,
            attempt_number=part.submit_attempts,
            provider=config.smppHost,
            status="ATTEMPTING",
            request_payload={
                "source_addr": source,
                "destination_addr": parent_msg.destination,
                "sequence_number": next_seq,
                "esm_class": part.esm_class,
                # Convert the raw bytes to hex so it saves safely in the JSON database field
                "hex_payload": final_msg.hex(),
            },
        )

        try:

            client.send_message(
                source_addr=source,
                destination_addr=parent_msg.destination,
                source_addr_ton=config.sourceTON,
                source_addr_npi=config.sourceNPI,
                dest_addr_ton=config.destTON,
                dest_addr_npi=config.destNPI,
                data_coding=0,  # Try 0 for standard GSM text
                esm_class=part.esm_class,
                short_message=final_msg,  # it contains the UDH + text chunk for multipart, or just text for single part
                registered_delivery=True,
                sequence=next_seq,  # Use our pre-generated sequence
            )

            # Wait a tiny bit for the response to be processed by read_once
            time.sleep(0.2)
            try:
                client.read_once()
            except:
                pass
            # 2. SUCCESS UPDATE (Record 'response_payload' and 'completed_at')
            attempt_log.status = "SUBMITTED"
            attempt_log.response_payload = {
                "status": "accepted_by_gateway",
                "sequence_number": next_seq,
            }
            attempt_log.completed_at = timezone.now()
            attempt_log.save()
            part.vendor_submit_status = 0
            part.submit_status = "SUBMITTED"
            part.submitted_at = timezone.now()
            part.save(
                update_fields=["vendor_submit_status", "submit_status", "submitted_at"]
            )

            if parent_msg.status == "queued":
                parent_msg.status = "submitted"
                parent_msg.submitted_at = timezone.now()
                parent_msg.save(update_fields=["status", "submitted_at"])

            self.stdout.write(self.style.SUCCESS(f"Processed Msg #{parent_msg.id}"))
        # ---> 1. CATCH IMMEDIATE VENDOR REJECTIONS (The Bouncer) <---
        except smpplib.exceptions.PDUError as pdu_err:
            now = timezone.now()

            # 1. Update Part with the exact integer status
            part.vendor_submit_status = pdu_err.status
            part.submit_status = "FAILED"
            part.failed_at = now
            part.failure_reason = (
                f"Rejected at submission. SMPP Error Code: {pdu_err.status}"
            )
            part.save(
                update_fields=[
                    "vendor_submit_status",
                    "submit_status",
                    "failed_at",
                    "failure_reason",
                ]
            )

            # 2. Update Parent Message
            parent_msg = part.message
            parent_msg.status = "failed"
            parent_msg.failed_at = now
            parent_msg.failure_reason = (
                f"Vendor Submission Error: SMPP Code {pdu_err.status}"
            )
            parent_msg.save(update_fields=["status", "failed_at", "failure_reason"])

            # 3. Update Attempt Log
            attempt_log.status = "FAILED"
            attempt_log.error_message = f"SMPP PDU Error: {pdu_err.status}"
            attempt_log.completed_at = now
            attempt_log.save()

            self.stdout.write(
                self.style.ERROR(
                    f"Vendor Rejected Msg #{parent_msg.id}: Code {pdu_err.status}"
                )
            )
        # ---> 2. CATCH EVERYTHING ELSE (Network drops, timeouts, crashes) <---
        except Exception as e:
            now = timezone.now()
            # 1. Update the specific Segment (Part)
            part.submit_status = "FAILED"
            part.failed_at = now  # <--- NEW: Track when it died
            part.failure_reason = str(e)  # <--- NEW: Store why it died
            part.save(update_fields=["submit_status", "failed_at", "failure_reason"])
            # 2. Update the Parent Message
            # If a submission fails at this stage, we mark the whole parent as failed
            parent_msg = part.message
            parent_msg.status = "failed"
            parent_msg.failed_at = now
            parent_msg.failure_reason = f"Submission Error: {str(e)}"
            parent_msg.save(update_fields=["status", "failed_at", "failure_reason"])

            # 3. Update the Attempt Log (Your existing code)
            attempt_log.status = "FAILED"
            attempt_log.error_message = str(e)
            attempt_log.completed_at = timezone.now()
            attempt_log.save()

            self.stdout.write(self.style.ERROR(f"Error: {e}"))

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

                part = (
                    SMSMessagePart.objects.filter(id=part_id)
                    .select_related("message")
                    .first()
                )
                if part:
                    part.vendor_msg_id = vendor_id
                    part.sent_at = timezone.now()
                    part.save(update_fields=["vendor_msg_id", "sent_at"])
                    parent = part.message
                    if not parent.sent_at:
                        parent.sent_at = timezone.now()
                        parent.save(update_fields=["sent_at"])
                    attempt = (
                        MessageAttempt.objects.filter(segment=part)
                        .order_by("-started_at")
                        .first()
                    )
                    if attempt:
                        attempt.provider_message_id = vendor_id
                        attempt.response_payload = {
                            "status": "accepted_by_gateway",
                            "vendor_msg_id": vendor_id,
                            "sequence_number": pdu.sequence,
                        }
                        attempt.save(
                            update_fields=["provider_message_id", "response_payload"]
                        )
                    # 2. UPDATE THE DETAILED REPORT (Master Record)
                    DetailedSMSReport.objects.filter(message=part.message).update(
                        vendor_msg_id=vendor_id  # Sync vendor ID to report for easy searching
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

    def sweep_stale_submissions(self):
        """
        Scans for messages that were sent to the vendor but never received a DLR
        within the acceptable timeout window (e.g., 24 hours).
        """
        # Define how long you are willing to wait for a vendor DLR (e.g., 24 hours)
        timeout_threshold = timezone.now() - timedelta(hours=24)

        stale_parts = SMSMessagePart.objects.filter(
            submit_status="SUBMITTED", submitted_at__lte=timeout_threshold
        ).select_related("message")

        count = stale_parts.count()
        if count == 0:
            return

        for part in stale_parts:
            # 1. Fail the specific part
            part.submit_status = "FAILED"
            part.failed_at = timezone.now()
            part.failure_reason = "Vendor Timeout: No DLR received within 24 hours."
            part.save(update_fields=["submit_status", "failed_at", "failure_reason"])

            # 2. Log it professionally in the Detailed Report
            DetailedSMSReport.objects.filter(message=part.message).update(
                submitStatus="FAILED"
            )

            # 3. Recalculate parent message status
            self.update_parent_message_status(part.message)

        logger.error(
            f"SYSTEM TIMEOUT: {count} messages were marked FAILED because the vendor never responded."
        )

    # it talks to the telecom vendor
    # it talks to the telecom vendor
    def handle_incoming(self, pdu, config):
        try:
            ERROR_DESCRIPTIONS = {
                "000": "Delivered successfully.",
                "001": "Subscriber Unavailable (Phone off or out of range).",
                "005": "Unknown Subscriber (Invalid or disconnected number).",
                "006": "Handset memory full.",
                "011": "Carrier SMSC queue full.",
                "013": "Blocked by Carrier Spam Filter.",
                "014": "Sender ID blocked or unregistered.",
                "078": "Restricted message content or Sender ID blocked.",  # ⚡️ ADDED 078
            }
            # When the vendor sends the Delivery Receipt (DLR), it arrives as raw computer bytes (zeros and ones).
            # This line converts those bytes into a readable Python string.
            content = pdu.short_message.decode("utf-8", errors="ignore")
            # Improved Regex to catch IDs like 7c6b98...
            # Think of Regex like using CTRL+F in a document, but supercharged.
            # It scans id in the DLR text and grabs the exact string of letters and numbers that come after "id:" and before the next space.
            match_id = re.search(r"id:([A-F0-9a-z]+)", content, re.IGNORECASE)
            # Catch REJECTD, DELIVRD.it scans the DLR text and grabs the exact status word that comes after "stat:" and before the next space.
            match_stat = re.search(r"stat:([A-Z]+)", content, re.IGNORECASE)
            # --- ADD THIS NEW REGEX ---
            # Grabs the 3-digit error code standard in SMPP DLRs
            match_err = re.search(r"err:([0-9a-zA-Z]+)", content, re.IGNORECASE)
            extracted_err_code = match_err.group(1) if match_err else ""

            # Ensure we actually found an ID and a Status in the DLR text
            if match_id and match_stat:
                v_id = match_id.group(1)
                v_stat = match_stat.group(1).upper()

                # ⚡️ THE SMART DESCRIPTION LOGIC ⚡️
                if v_stat == "DELIVRD" and extracted_err_code == "000":
                    human_description = "Delivered successfully."
                elif (
                    v_stat in ["REJECTD", "UNDELIV", "EXPIRED", "FAILED"]
                    and extracted_err_code == "000"
                ):
                    human_description = (
                        "Generic Vendor Rejection (No specific error code provided)."
                    )
                else:
                    human_description = ERROR_DESCRIPTIONS.get(
                        extracted_err_code, f"Vendor Error ({extracted_err_code})"
                    )

                # The bright console log for easy debugging
                print("\n" + "!" * 50)
                print(f"🚨 VENDOR DLR RECEIVED 🚨")
                print(f"Raw DLR String: {content}")
                print(f"Extracted Error Code: {extracted_err_code}")
                print(f"Error Meaning: {human_description}")
                print("!" * 50 + "\n")

                status_map = {
                    "DELIVRD": "DELIVERED",
                    "REJECTD": "FAILED",
                    "UNDELIV": "FAILED",
                    "EXPIRED": "FAILED",
                    "DELETED": "FAILED",
                    "UNKNOWN": "FAILED",
                }
                new_status = status_map.get(v_stat, "SUBMITTED")

                part = (
                    SMSMessagePart.objects.filter(vendor_msg_id=v_id)
                    .select_related("message")
                    .first()
                )

                if part:
                    part.submit_status = new_status
                    now = timezone.now()
                    if new_status == "DELIVERED":
                        part.delivered_at = now
                        part.save(update_fields=["submit_status", "delivered_at"])
                    elif new_status == "FAILED":
                        part.failed_at = now
                        part.failure_reason = content
                        part.save(
                            update_fields=[
                                "submit_status",
                                "failed_at",
                                "failure_reason",
                            ]
                        )

                    attempt = (
                        MessageAttempt.objects.filter(segment=part)
                        .order_by("-started_at")
                        .first()
                    )
                    if attempt:
                        attempt.status = new_status
                        attempt.completed_at = now
                        fields_to_update = ["status", "completed_at"]
                        if new_status == "FAILED":
                            attempt.error_message = (
                                f"Vendor DLR Error: {extracted_err_code}"
                            )
                            fields_to_update.append("error_message")
                        attempt.save(update_fields=fields_to_update)

                    # ⚡️ SAVING THE SMART DESCRIPTION TO THE DATABASE
                    DLREvent.objects.create(
                        message=part.message,
                        segment=part,
                        provider_message_id=v_id,
                        event_type=new_status,
                        segment_number=part.part_no,
                        raw_payload={"raw_smpp_string": content},
                        status_code=extracted_err_code,
                        status_description=human_description,  # This is where the fix is applied!
                    )

                    self.update_parent_message_status(part.message)
                    print(
                        f"--- Updated Part with Vendor ID {v_id} to status {new_status} ---"
                    )

                    update_data = {"submitStatus": new_status}
                    if new_status == "DELIVERED":
                        update_data["delivery_time"] = timezone.now()

                    DetailedSMSReport.objects.filter(vendor_msg_id__iexact=v_id).update(
                        **update_data
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f"DLR: {v_id} is now {new_status}")
                    )
            else:
                print(
                    f"--- DEBUG: DLR received but missing ID or STAT. Content: {content} ---"
                )

        except Exception as e:
            logger.error(f"DLR Error: {e}")

    def update_parent_message_status(self, parent_msg):
        """Calculates the overall status of a message based on its parts."""

        # Get all parts for this parent message
        all_parts = SMSMessagePart.objects.filter(message=parent_msg)
        total_parts = all_parts.count()

        delivered_count = all_parts.filter(submit_status="DELIVERED").count()
        failed_parts = all_parts.filter(submit_status="FAILED")
        failed_count = failed_parts.count()

        new_parent_status = parent_msg.status

        if delivered_count == total_parts:
            new_parent_status = "delivered"
        elif failed_count == total_parts:
            new_parent_status = "failed"
        elif delivered_count > 0 and (delivered_count + failed_count == total_parts):
            # Some delivered, some failed, and no more are pending
            new_parent_status = "failed"  # partially_delivered

        # Only hit the database if the status actually changed
        if new_parent_status != parent_msg.status or failed_count > 0:
            parent_msg.status = new_parent_status
            now = timezone.now()
            detailed_reason = None
            if failed_count > 0:
                reasons = []
                for part in failed_parts:
                    # Use the segment's failure reason, or a default if it's missing
                    reason_text = (
                        part.failure_reason
                        if part.failure_reason
                        else "Unknown vendor error."
                    )
                    reasons.append(f"Part {part.part_no}/{total_parts}: {reason_text}")

                # Combine all reasons into a single string separated by newlines
                detailed_reason = " | ".join(reasons)
            # -------------------------------------
            if new_parent_status == "delivered":
                parent_msg.delivered_at = now
            elif new_parent_status == "failed":
                parent_msg.failed_at = now
                parent_msg.failure_reason = f"All segments failed. {detailed_reason}"
            elif new_parent_status == "failed":  # partially_delivered
                # For partial, we still set delivered_at because SOME of it
                # reached the user, but we add a note to the failure reason.
                parent_msg.delivered_at = now
                parent_msg.failure_reason = f"Partial delivery ({delivered_count}/{total_parts} succeeded). {detailed_reason}"
            parent_msg.save(
                update_fields=["status", "delivered_at", "failed_at", "failure_reason"]
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"Parent Msg #{parent_msg.id} is now {new_parent_status}"
                )
            )
