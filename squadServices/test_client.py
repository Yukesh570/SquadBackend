import smpplib.gsm
import smpplib.client
import smpplib.consts

# client = smpplib.client.Client("192.168.1.88", 2775)
client = smpplib.client.Client("192.168.10.3", 2775)

print("Connecting to server...")
client.connect()

client.bind_transceiver(system_id="yukesh", password="maharjan")
print("Successfully")

print("Sending SMS...")
msg = "Hello tester!!!!"

client.send_message(
    source_addr_ton=smpplib.consts.SMPP_TON_INTL,
    source_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
    source_addr="9801234567",
    dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
    dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
    destination_addr="986283638",
    short_message=msg.encode("utf-8"),
)

print("Message Sent!")

client.disconnect()
