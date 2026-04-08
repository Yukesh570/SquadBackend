import smpplib.gsm
import smpplib.client
import smpplib.consts
import smpplib.exceptions
import sys  # <-- Used to stop the script safely

# Configuration
SERVER_IP = "192.168.10.3"
PORT = 2775

client = smpplib.client.Client(SERVER_IP, PORT)


def handle_sent_sms(pdu):
    """This runs if the server returns Status 0"""
    print(f"\n--- SMS Sent Handler --- Status: {pdu.status}")
    if pdu.status == 0:
        print(f"DEBUG: Raw ID from Server: {pdu.message_id}")
        msg_id = (
            pdu.message_id.decode("ascii", errors="ignore")
            if isinstance(pdu.message_id, bytes)
            else pdu.message_id
        )

        # ⚡️ THE MAGIC: Check if the ID is actually our Trojan Horse error!
        if msg_id.startswith("ERR:"):
            print(f"\n⚠️ SQUAD SERVER REJECTED MESSAGE")
            print(f"❌ SQUAD REASON: {msg_id[4:].strip()}")
        else:
            print(f"\n✅ SMS Accepted by Squad!")
            print(f"Unique Message ID: {msg_id}")


def handle_deliver_sm(pdu):
    """This handles incoming DLRs"""
    print(f"\n--- DLR Received ---")
    print(f"Data: {pdu.short_message.decode('utf-8', errors='ignore')}")


# You fire the message: client.send_message(...) pushes the SMS data into the TCP socket and out to your Django server. The client doesn't wait; it immediately moves to the next line of code.

# You wait for the reply: client.listen() pauses the script and waits for the server to say something back.

# The Server Replies: Your Django server finishes processing the message and sends back a submit_sm_resp packet.

# Path A (Status == 0): The library says, "Great, it was a success!" and it immediately calls your
# Register handlers
# server sends back a Response.

# when client sends message to server, the server will respond with a submit_sm_resp, which will trigger the handle_sent_sms function.
client.set_message_sent_handler(handle_sent_sms)
# If the server sends a deliver_sm (DLR), it will trigger the handle_deliver_sm function.
client.set_message_received_handler(handle_deliver_sm)

# ⚡️ EVERYTHING is now safely inside the try block
try:
    print(f"Connecting to Squad Server at {SERVER_IP}...")
    client.connect()
    client.bind_transceiver(system_id="yukesh", password="yukesh")
    print("✅ Successfully Bound")

    print("Sending SMS...")
    msg = " 😊There is a awarness program today,The prograssssssssssssaaaaaaaaaaaaaaaaasssssssm is very important,The program will st be able to get in please call 9801234567"
    pdu = client.send_message(
        source_addr_ton=5,
        source_addr_npi=0,
        source_addr="SQUAD",
        dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
        dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
        destination_addr="+573213389839",
        short_message=msg.encode("utf-8"),
        data_coding=0,  # 8=UCS2, 0=GSM7
        registered_delivery=True,
    )
    # Listen for responses
    client.listen()

except smpplib.exceptions.PDUError as e:
    # This catches ANY strict protocol error (Bind 13/15, or Submit 11)
    status_code = (
        e.args[1] if len(e.args) >= 2 and isinstance(e.args[1], int) else "Unknown"
    )

    print("\n⚠️ SQUAD SERVER REJECTED REQUEST")
    # if status_code == 12:
    #     print("❌ REASON: Invalid Destination Number")
    # elif status_code == 13:
    #     print("❌ REASON: IP Address Not Whitelisted (Or Invalid System ID)")
    # elif status_code == 15:
    #     print("❌ REASON: Invalid Password")
    # else:
    print(f"❌ PROTOCOL REASON: Status Code {status_code}")

    sys.exit(1)  # Stop the script safely

except Exception as e:
    print(f"\n❌ CRITICAL ERROR: {e}")
    sys.exit(1)

finally:
    print("\nDisconnecting...")
    # Safe disconnect check
    if hasattr(client, "state") and client.state in [
        smpplib.consts.SMPP_CLIENT_STATE_BOUND_TX,
        smpplib.consts.SMPP_CLIENT_STATE_BOUND_RX,
        smpplib.consts.SMPP_CLIENT_STATE_BOUND_TRX,
    ]:
        client.disconnect()
