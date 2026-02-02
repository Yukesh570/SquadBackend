import time
import logging
import socket
import smpplib.gsm
import smpplib.client
import smpplib.consts
from django.core.management.base import BaseCommand
from squadServices.models.smpp.smppSMS import SMSMessage

# Configure logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs the SMPP Client Listener"

    def handle(self, *args, **options):
        # --- CONFIGURATION ---
        # ip = "127.0.0.1"
        # port = 2775
        # system_id = "squad_user"
        # password = "squad123"
        ip = "135.181.134.183"
        port = 7210
        system_id = "AAMI_DIR1"
        password = "CD9RQ4uj"
        # ---------------------

        self.stdout.write(f"Starting SMPP Client for {system_id} on {ip}:{port}...")

        while True:
            client = None
            try:
                # Initialize Client with a socket timeout
                client = smpplib.client.Client(ip, port, timeout=5)

                # 1. Handle Incoming Messages (MO)
                client.set_message_received_handler(
                    lambda pdu: self.handle_incoming_message(pdu)
                )

                # 2. Handle Delivery Receipts (DLR)
                client.set_message_sent_handler(
                    lambda pdu: self.handle_sent_confirmation(pdu)
                )

                # Connect
                client.connect()

                # Bind (Login)
                client.bind_transceiver(system_id=system_id, password=password)

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Connected successfully as {system_id}. Listening..."
                    )
                )

                # 3. Main Loop
                while True:
                    try:
                        # Check for incoming traffic (Wait up to 5 seconds)
                        client.read_once()
                    except socket.timeout:
                        pass  # Expected timeout, continue to sending logic

                    # Process Outgoing Messages from DB
                    self.process_outgoing_queue(client)

            except smpplib.exceptions.PDUError as e:
                logger.error(f"SMPP PDU Error: {e}")
                self.stdout.write(
                    self.style.ERROR(
                        f"Login/PDU failed (Error {e.args[1] if e.args else '?'}). Retrying in 30 seconds..."
                    )
                )
                if client:
                    client.disconnect()
                time.sleep(30)

            except smpplib.exceptions.ConnectionError:
                logger.error("Connection lost. Retrying in 5 seconds...")
                if client:
                    client.disconnect()
                time.sleep(5)

            except KeyboardInterrupt:
                self.stdout.write("Stopping SMPP Client...")
                if client:
                    try:
                        client.unbind()
                        client.disconnect()
                    except:
                        pass
                break

            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                self.stdout.write(self.style.ERROR(f"Unexpected error: {e}"))
                if client:
                    client.disconnect()
                time.sleep(5)

    def handle_incoming_message(self, pdu):
        """Handle incoming SMS from users"""
        try:
            text = pdu.short_message.decode("utf-8")
        except:
            text = pdu.short_message.decode("latin-1")

        logger.info(f"Received SMS: {text} from {pdu.source_addr}")
        self.stdout.write(f"Incoming SMS from {pdu.source_addr}: {text}")

    def handle_sent_confirmation(self, pdu):
        """Handle Delivery Receipts (DLR)"""
        logger.info(f"Message Sent Confirmation. ID: {pdu.message_id}")

    def process_outgoing_queue(self, client):
        """Check DB for 'queued' messages and send them"""
        queued_msgs = SMSMessage.objects.filter(status="queued").order_by("createdAt")[
            :5
        ]

        for msg in queued_msgs:
            try:
                if msg.systemId:
                    route_key = msg.systemId

                    # Optional: Get TON/NPI from vendor model if they exist
                    # s_ton = getattr(msg.vendor, 'sourceTON', 5) # Default to 5 (Alphanumeric)
                    # d_ton = getattr(msg.vendor, 'destTON', 1)   # Default to 1 (International)
                else:
                    # Fallback if no vendor assigned (prevents crash)
                    route_key = "SQUAD_DEFAULT"

                print(f"DEBUG: Routing message via {route_key}")
                # -----------------------------
                parts, encoding_flag, msg_type_flag = smpplib.gsm.make_parts(msg.text)

                for part in parts:
                    client.send_message(
                        source_addr=route_key,  # This is 9801234567
                        destination_addr=msg.destination,  # This is 9779863480429
                        short_message=part,
                        # --- THE FIX STARTS HERE ---
                        # Destination: TON 1 (International) + NPI 1 (E.164 Standard)
                        dest_addr_ton=1,
                        dest_addr_npi=1,
                        # Source: Since 9801234567 is a number, use TON 1 (International)
                        # If it was a name like "SQUAD", use TON 5 (Alphanumeric)
                        source_addr_ton=1 if route_key.isdigit() else 5,
                        source_addr_npi=1 if route_key.isdigit() else 0,
                        # ---------------------------
                        data_coding=encoding_flag,
                        esm_class=msg_type_flag,
                        registered_delivery=True,
                    )
                msg.status = "sent"
                msg.save()
                self.stdout.write(
                    self.style.SUCCESS(f"Sent message to {msg.destination}")
                )
                logger.info(f"Sent message to {msg.destination}")

            except Exception as e:
                logger.error(f"Failed to send to {msg.destination}: {str(e)}")
                self.stdout.write(
                    self.style.ERROR(f"Failed to send to {msg.destination}: {e}")
                )
                msg.status = "failed"
                msg.save()
