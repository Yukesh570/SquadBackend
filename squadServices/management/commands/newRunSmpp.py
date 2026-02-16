import time
import logging
import socket
import re
import smpplib.gsm
import smpplib.client
import smpplib.consts
from django.core.management.base import BaseCommand
from squadServices.models.smpp.smppSMS import SMSMessage
from squadServices.models.connectivityModel.smpp import SMPP

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs a Multi-Gateway SMPP Client Manager"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sessions = {}
        # This maps the SMPP Sequence Number to our Database ID
        self.sequence_to_msg_id = {}

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting Multi-Gateway SMPP Manager..."))

        while True:
            try:
                # STEP 1: Process Outgoing Queue
                queued_msgs = SMSMessage.objects.filter(status="queued").order_by(
                    "createdAt"
                )[:10]

                for msg in queued_msgs:
                    if not msg.smpp:
                        msg.status = "failed"
                        msg.save()
                        continue

                    smpp_id = msg.smpp.id

                    # Connection Management
                    if smpp_id not in self.sessions:
                        last_attempt = getattr(self, f"last_attempt_{smpp_id}", 0)
                        if time.time() - last_attempt < 10:
                            continue

                        setattr(self, f"last_attempt_{smpp_id}", time.time())
                        self.stdout.write(f"Connecting to {msg.smpp.smppHost}...")
                        client = self.connect_to_gateway(msg.smpp)

                        if client:
                            self.sessions[smpp_id] = client
                        else:
                            continue

                    # Send the message
                    client = self.sessions[smpp_id]
                    self.send_single_message(client, msg, msg.smpp)

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

                if not queued_msgs:
                    time.sleep(1)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Global Loop Error: {e}")
                time.sleep(2)

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

    def send_single_message(self, client, msg, config):
        try:
            source = msg.systemId if msg.systemId else config.systemID
            parts, encoding, msg_type = smpplib.gsm.make_parts(msg.text)

            for part in parts:
                # Respect Vendor speed limits to avoid Error 69
                time.sleep(1.0)

                # Send and record the sequence number
                sequence = client.send_message(
                    source_addr=source,
                    destination_addr=msg.destination,
                    short_message=part,
                    source_addr_ton=config.sourceTON,
                    source_addr_npi=config.sourceNPI,
                    dest_addr_ton=config.destTON,
                    dest_addr_npi=config.destNPI,
                    data_coding=encoding,
                    esm_class=msg_type,
                    registered_delivery=True,
                )

                # Map this specific sequence to our database ID
                self.sequence_to_msg_id[sequence] = msg.id

                # Try to catch the response immediately
                try:
                    client.read_once()
                except socket.timeout:
                    pass

            msg.status = "sent"
            msg.save()
            self.stdout.write(self.style.SUCCESS(f"Processed Msg #{msg.id}"))

        except Exception as e:
            # This is the most reliable way to see what is happening
            error_text = str(e)
            self.stdout.write(
                self.style.ERROR(
                    f"Vendor Rejected Msg #{msg.id}. Raw Error: {error_text}"
                )
            )

            # If the error text contains "69", we know it's Throttling/Balance
            if "69" in error_text:
                self.stdout.write(
                    self.style.WARNING("Detected Error 69: Balance or Speed limit hit.")
                )
                time.sleep(5)

            msg.status = "failed"
            msg.save()

    def handle_sent_confirmation(self, pdu):
        """When the vendor accepts the msg, they give us their Tracking ID"""
        vendor_id = pdu.message_id.decode("ascii").strip("\x00")
        db_id = self.sequence_to_msg_id.get(pdu.sequence)

        if db_id:
            # KEY STEP: Link the vendor's tracking ID to our database row
            SMSMessage.objects.filter(id=db_id).update(message_id=vendor_id)
            self.stdout.write(f"Linked Msg #{db_id} to Vendor ID: {vendor_id}")
            del self.sequence_to_msg_id[pdu.sequence]

    def handle_incoming(self, pdu, config):
        """Handle Delivery Reports (DLRs)"""
        try:
            content = pdu.short_message.decode("utf-8", errors="ignore")

            # Regex to find id:XXXX and stat:YYYY
            match_id = re.search(r"id:([A-F0-9a-z]+)", content)
            match_stat = re.search(r"stat:([A-Z]+)", content)

            if match_id and match_stat:
                v_id = match_id.group(1)
                v_stat = match_stat.group(1)

                status_map = {
                    "DELIVRD": "delivered",
                    "UNDELIV": "failed",
                    "REJECTD": "failed",
                    "EXPIRED": "failed",
                }
                new_status = status_map.get(v_stat, "sent")

                # Find the message using the Vendor's ID we saved earlier
                updated = SMSMessage.objects.filter(message_id=v_id).update(
                    status=new_status
                )
                if updated:
                    self.stdout.write(
                        self.style.SUCCESS(f"DLR Update: {v_id} is now {new_status}")
                    )
        except Exception as e:
            logger.error(f"DLR Parsing Error: {e}")
