import time
import logging
import socket
import smpplib.gsm
import smpplib.client
import smpplib.consts
from django.core.management.base import BaseCommand
from squadServices.models.smpp.smppSMS import SMSMessage
from squadServices.models.connectivityModel.smpp import SMPP

# Configure logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs a Multi-Gateway SMPP Client Manager"

    def handle(self, *args, **options):
        self.stdout.write("Starting Multi-Gateway SMPP Manager...")

        # Dictionary to hold active connections: { smpp_id: client_instance }
        self.sessions = {}

        while True:
            try:
                # ---------------------------------------------------------
                # STEP 1: Process Outgoing Queue (Dynamic Routing)
                # ---------------------------------------------------------
                # Fetch all queued messages
                queued_msgs = SMSMessage.objects.filter(status="queued").order_by(
                    "createdAt"
                )[:10]

                for msg in queued_msgs:
                    if not msg.smpp:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Msg {msg.id} has no SMPP Gateway assigned. Skipping."
                            )
                        )
                        msg.status = "failed"
                        msg.save()
                        continue

                    smpp_id = msg.smpp.id
                    # At the top of your class
                    self.retry_delays = {}  # {smpp_id: current_delay_seconds}

                    # Inside the loop where you connect:
                    if smpp_id not in self.sessions:
                        # 1. Simple 10-second check
                        last_attempt = getattr(self, f"last_attempt_{smpp_id}", 0)
                        if time.time() - last_attempt < 10:
                            continue  # Skip this gateway and move to the next message

                        # 2. Update the timestamp immediately so other messages in this loop skip it too
                        setattr(self, f"last_attempt_{smpp_id}", time.time())

                        self.stdout.write(f"Connecting to {msg.smpp.smppHost}...")
                        client = self.connect_to_gateway(msg.smpp)

                        if client:
                            self.sessions[smpp_id] = client
                        else:
                            # 3. Use the message you wanted
                            self.stdout.write(
                                self.style.WARNING(
                                    f"Failed to connect to Gateway ID {smpp_id}. Retrying in 10s."
                                )
                            )
                            continue

                    # Get the active client and send
                    client = self.sessions[smpp_id]
                    self.send_single_message(client, msg, msg.smpp)

                # ---------------------------------------------------------
                # STEP 2: Listen for Incoming Traffic on ALL Active Sessions
                # ---------------------------------------------------------
                # We iterate a copy of keys/values because we might remove disconnected clients
                for smpp_id, client in list(self.sessions.items()):
                    try:
                        # Very short timeout so we don't block other gateways
                        client.read_once()
                    except socket.timeout:
                        pass  # No data received, move to next
                    except (smpplib.exceptions.ConnectionError, OSError):
                        self.stdout.write(
                            self.style.ERROR(
                                f"Connection lost for Gateway ID {smpp_id}"
                            )
                        )
                        try:
                            client.disconnect()
                        except:
                            pass
                        del self.sessions[smpp_id]  # Remove dead session

                # Small sleep to prevent CPU spiking if queue is empty
                if not queued_msgs:
                    time.sleep(1)

            except KeyboardInterrupt:
                self.stdout.write("Stopping all connections...")
                for client in self.sessions.values():
                    try:
                        client.disconnect()
                    except:
                        pass
                break
            except Exception as e:
                logger.error(f"Global Error: {e}")
                time.sleep(1)

    def connect_to_gateway(self, smpp_config):
        """Helper to establish a new SMPP connection"""
        try:
            client = smpplib.client.Client(
                smpp_config.smppHost, smpp_config.smppPort, timeout=1
            )  # Short timeout for loop

            # Register Handlers
            client.set_message_received_handler(
                lambda pdu: self.handle_incoming(pdu, smpp_config)
            )
            client.set_message_sent_handler(
                lambda pdu: self.handle_sent_confirmation(pdu)
            )

            client.connect()

            # Bind based on Config
            mode = smpp_config.bindMode.upper()
            system_id = smpp_config.systemID
            password = smpp_config.password

            if mode == "TRANSMITTER":
                client.bind_transmitter(system_id=system_id, password=password)
            elif mode == "RECEIVER":
                client.bind_receiver(system_id=system_id, password=password)
            else:
                client.bind_transceiver(system_id=system_id, password=password)

            self.stdout.write(
                self.style.SUCCESS(f"Connected to {smpp_config.smppHost} ({system_id})")
            )
            return client

        except Exception as e:
            logger.error(f"Connection Error for {smpp_config.smppHost}: {e}")
            return None

    def send_single_message(self, client, msg, smpp_config):
        """Helper to send one message"""
        try:
            source = msg.systemId if msg.systemId else smpp_config.systemID

            print(f"Routing Msg #{msg.id} via {smpp_config.smppHost}...")

            parts, encoding, msg_type = smpplib.gsm.make_parts(msg.text)

            for part in parts:
                client.send_message(
                    source_addr=source,
                    destination_addr=msg.destination,
                    short_message=part,
                    source_addr_ton=smpp_config.sourceTON,
                    source_addr_npi=smpp_config.sourceNPI,
                    dest_addr_ton=smpp_config.destTON,
                    dest_addr_npi=smpp_config.destNPI,
                    data_coding=encoding,
                    esm_class=msg_type,
                    registered_delivery=True,
                )

            msg.status = "sent"
            msg.save()
            self.stdout.write(self.style.SUCCESS(f"Sent Msg #{msg.id}"))

        except Exception as e:
            logger.error(f"Send Failed: {e}")
            msg.status = "failed"
            msg.save()

    def handle_incoming(self, pdu, smpp_config):
        """Handle Inbound SMS"""
        try:
            text = pdu.short_message.decode("utf-8")
        except:
            text = pdu.short_message.decode("latin-1")

        self.stdout.write(
            f"Incoming from {pdu.source_addr} via {smpp_config.smppHost}: {text}"
        )

        # Save to DB if needed
        # SMSMessage.objects.create(..., status="received", smpp=smpp_config)

    def handle_sent_confirmation(self, pdu):
        logger.info(f"DLR Received: {pdu.message_id}")
