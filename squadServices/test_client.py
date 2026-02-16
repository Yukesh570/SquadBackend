import smpplib.gsm
import smpplib.client
import smpplib.consts
import time

client = smpplib.client.Client("192.168.20.3", 2775)
# client = smpplib.client.Client("193.180.215.190", 2775)

print("Connecting to server...")
client.connect()
client.bind_transceiver(system_id="yukesh", password="android")
print("Successfully Bound")


# 1. Define the handler for the SUBMIT_SM_RESP (The unique ID)
def handle_sent_sms(pdu):
    print(f"--- Server confirmed receipt! ---")
    print(f"Unique Message ID: {pdu.message_id}")


# 2. Define a handler for the DELIVER_SM (The DLR)
def handle_deliver_sm(pdu):
    print(f"--- DLR Received from Server! ---")
    print(f"Status Data: {pdu.short_message}")


client.set_message_sent_handler(handle_sent_sms)
client.set_message_received_handler(handle_deliver_sm)

print("Sending SMS...")
msg = "Hi my name is yukesh maharjan. i live in chobhar kathmandu"

# 3. Send the message first
client.send_message(
    source_addr_ton=smpplib.consts.SMPP_TON_INTL,
    source_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
    source_addr="9801234567",
    dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
    dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
    destination_addr="986283638",
    short_message=msg.encode("utf-8"),
)

print("Message Sent! Now waiting for ID and DLR...")

# 4. NOW listen for the server's response (Unique ID) and the DLR
# This will stay open until a packet arrives or you stop it (Ctrl+C)
client.listen()

client.disconnect()
