import secrets

import smpplib.gsm
import smpplib.client
import smpplib.consts
import smpplib.exceptions
import sys  # <-- Used to stop the script safely

# Configuration
SERVER_IP = "192.168.1.191"
PORT = 2776

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
            print(f"⚠️ SQUAD SERVER REJECTED MESSAGE")
            print(f"❌ SQUAD REASON: {msg_id[4:].strip()}")
        else:
            print(f"✅ SMS Part Accepted by Squad! ID: {msg_id}")


def handle_deliver_sm(pdu):
    """This handles incoming DLRs and automatically detects encoding"""
    print(f"\n--- DLR Received ---")
    try:
        # If data_coding is 8, it's UCS2 (UTF-16)
        if pdu.data_coding == 8:
            msg = pdu.short_message.decode("utf-16-be", errors="ignore")
        else:
            msg = pdu.short_message.decode("utf-8", errors="ignore")
        print(f"Data: {msg}")
    except Exception as e:
        print(f"Decode Error: {e}")
        # Fallback to raw if decoding fails
        print(f"Raw Data: {pdu.short_message}")


# client.set_message_sent_handler(handle_sent_sms)
client.set_message_received_handler(handle_deliver_sm)


try:
    print(f"Connecting to Squad Server at {SERVER_IP}...")
    client.connect()
    client.bind_transceiver(system_id="sunil", password="suni2056")
    print("✅ Successfully Bound")

    # msg = "⚡️ SQUAD ALERT: This is a test message to demonstrate automatic splitting of long messages with emojis!😊"

    # ____________________tlv__________________
    msg = "⚡️ SQUAD ALERT: ThR splitting with emojis! 😊 "
    msg_bytes = msg.encode("utf-16-be")
    parts, encoding_flag, msg_type_flag = smpplib.gsm.make_parts(msg)
    client.send_message(
        source_addr_ton=5,
        source_addr_npi=0,
        source_addr="SQUAD",
        dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
        dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
        destination_addr="+573213389839",
        short_message=msg_bytes,
        data_coding=8,
        esm_class=0,  # This tells the server it's a segmented message with UDH
        registered_delivery=True,
    )

    # Listen for all the responses
    client.listen()

except smpplib.exceptions.PDUError as e:
    # This catches ANY strict protocol error (Bind 13/15, or Submit 11)
    status_code = (
        e.args[1] if len(e.args) >= 2 and isinstance(e.args[1], int) else "Unknown"
    )
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
