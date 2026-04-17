import secrets

import smpplib.gsm
import smpplib.client
import smpplib.consts
import smpplib.exceptions
import sys  # <-- Used to stop the script safely

# Configuration
SERVER_IP = "192.168.1.191"
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
            print(f"⚠️ SQUAD SERVER REJECTED MESSAGE")
            print(f"❌ SQUAD REASON: {msg_id[4:].strip()}")
        else:
            print(f"✅ SMS Part Accepted by Squad! ID: {msg_id}")


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


# The SMPP protocol has a strict, hardcoded rule: the short_message parameter cannot be larger than 254 bytes.

# ___________________________for UDH___________________________
# ⚡️ EVERYTHING is now safely inside the try block
try:
    print(f"Connecting to Squad Server at {SERVER_IP}...")
    client.connect()
    client.bind_transceiver(system_id="yukesh", password="yukesh")
    print("✅ Successfully Bound")

    print("\nPreparing MASSIVE SMS for splitting...")
    # msg = "⚡️ SQUAD ALERT: This is a test message to demonstrate automatic splitting of long messages with emojis!😊"

    # ____________________tlv__________________
    msg = (
        "⚡️ SQUAD ALERT:hellso!This is a test message to demonstrate SAR splitting with emojis! 😊 "
        * 2
    )
    raw_bytes = msg.encode("utf-16-be")

    # Slice the bytes into chunks of 140

    # ____________________tlv__________________

    # base_sentence = "There is an awareness program today, please call 9801234567. "
    # msg = "😊 " + (base_sentence * 12)
    # 1. ⚡️ THE SPLITTER: Let the library calculate the chunks, the UDH, and the encoding!
    parts, encoding_flag, msg_type_flag = smpplib.gsm.make_parts(msg)  # for udh
    sar_reference_number = secrets.randbelow(65535)
    print("parts", parts)
    print("encoding_flag", encoding_flag)
    print("msg_type_flag", msg_type_flag)
    print(
        f"📦 Message automatically split into {len(parts)} parts! Firing them at the server..."
    )

    # 2. ⚡️ THE LOOP: Fire each part over the network separately
    for i, part in enumerate(parts):
        print(f"   -> Firing Part {i+1}...")
        client.send_message(
            source_addr_ton=5,
            source_addr_npi=0,
            source_addr="SQUAD",
            dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
            dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
            destination_addr="+573213389839",
            # destination_addr="+9779851047370",
            # Send the specific binary chunk (which now has the UDH prepended to it)
            short_message=part,
            # The library automatically figured out we need UCS-2 (8) because of the emojis
            data_coding=encoding_flag,
            # The library automatically turns on the 0x40 bit to tell your server it's multipart
            esm_class=msg_type_flag,
            registered_delivery=True,
        )

    # Listen for all the responses
    client.listen()

except smpplib.exceptions.PDUError as e:
    # This catches ANY strict protocol error (Bind 13/15, or Submit 11)
    status_code = (
        e.args[1] if len(e.args) >= 2 and isinstance(e.args[1], int) else "Unknown"
    )

    print("\n⚠️ SQUAD SERVER REJECTED REQUEST")
    if status_code == 12:
        print("❌ REASON: Invalid Destination Number")
    elif status_code == 13:
        print("❌ REASON: IP Address Not Whitelisted (Or Invalid System ID)")
    elif status_code == 15:
        print("❌ REASON: Invalid Password")
    else:
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


# ___________________________for tlv testing with segments___________________________
# # ⚡️ EVERYTHING is now safely inside the try block
# try:
#     print(f"Connecting to Squad Server at {SERVER_IP}...")
#     client.connect()
#     client.bind_transceiver(system_id="yukesh", password="yukesh")
#     print("✅ Successfully Bound")

#     print("\nPreparing MASSIVE SMS for splitting...")
#     # msg = "⚡️ SQUAD ALERT: This is a test message to demonstrate automatic splitting of long messages with emojis!😊"

#     # ____________________tlv__________________
#     msg = (
#         "⚡️ SQUAD ALERT: This is a test message to demonstrate SAR splitting with emojis! 😊 "
#         * 4
#     )
#     raw_bytes = msg.encode("utf-16-be")
#     chunk_size = 140  # Max payload size for UCS-2 when there is no UDH header

#     # Slice the bytes into chunks of 140
#     parts = [
#         raw_bytes[i : i + chunk_size] for i in range(0, len(raw_bytes), chunk_size)
#     ]
#     total_parts = len(parts)
#     # ____________________tlv__________________

#     # base_sentence = "There is an awareness program today, please call 9801234567. "
#     # msg = "😊 " + (base_sentence * 12)
#     # 1. ⚡️ THE SPLITTER: Let the library calculate the chunks, the UDH, and the encoding!
#     # parts, encoding_flag, msg_type_flag = smpplib.gsm.make_parts(msg)   #for udh
#     sar_reference_number = secrets.randbelow(65535)
#     # print("parts", parts)
#     # print("encoding_flag", encoding_flag)
#     # print("msg_type_flag", msg_type_flag)
#     # print(
#     #     f"📦 Message automatically split into {len(parts)} parts! Firing them at the server..."
#     # )

#     # 2. ⚡️ THE LOOP: Fire each part over the network separately
#     for i, part in enumerate(parts):
#         print(f"   -> Firing Part {i+1}...")
#         # client.send_message(
#         #     source_addr_ton=5,
#         #     source_addr_npi=0,
#         #     source_addr="SQUAD",
#         #     dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
#         #     dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
#         #     destination_addr="+573213389839",
#         #     # destination_addr="+9779851047370",
#         #     # Send the specific binary chunk (which now has the UDH prepended to it)
#         #     short_message=part,
#         #     # The library automatically figured out we need UCS-2 (8) because of the emojis
#         #     data_coding=encoding_flag,
#         #     # The library automatically turns on the 0x40 bit to tell your server it's multipart
#         #     esm_class=msg_type_flag,
#         #     registered_delivery=True,
#         # )
#         client.send_message(
#             source_addr_ton=5,
#             source_addr_npi=0,
#             source_addr="SQUAD",
#             dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
#             dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
#             destination_addr="+573213389839",
#             # The clean, UDH-free text bytes
#             short_message=part,
#             # We are using emojis, so force UCS-2
#             data_coding=8,
#             # ⚡️ CRITICAL: Set to 0! Do NOT use 0x40 because there is no UDH inside the payload
#             esm_class=0,
#             registered_delivery=True,
#             # ⚡️ THE SAR TLVS (Optional Parameters)
#             sar_msg_ref_num=sar_reference_number,
#             sar_total_segments=total_parts,
#             sar_segment_seqnum=i + 1,
#         )

#     # Listen for all the responses
#     client.listen()

# except smpplib.exceptions.PDUError as e:
#     # This catches ANY strict protocol error (Bind 13/15, or Submit 11)
#     status_code = (
#         e.args[1] if len(e.args) >= 2 and isinstance(e.args[1], int) else "Unknown"
#     )

#     print("\n⚠️ SQUAD SERVER REJECTED REQUEST")
#     if status_code == 12:
#         print("❌ REASON: Invalid Destination Number")
#     elif status_code == 13:
#         print("❌ REASON: IP Address Not Whitelisted (Or Invalid System ID)")
#     elif status_code == 15:
#         print("❌ REASON: Invalid Password")
#     else:
#         print(f"❌ PROTOCOL REASON: Status Code {status_code}")

#     sys.exit(1)  # Stop the script safely

# except Exception as e:
#     print(f"\n❌ CRITICAL ERROR: {e}")
#     sys.exit(1)

# finally:
#     print("\nDisconnecting...")
#     # Safe disconnect check
#     if hasattr(client, "state") and client.state in [
#         smpplib.consts.SMPP_CLIENT_STATE_BOUND_TX,
#         smpplib.consts.SMPP_CLIENT_STATE_BOUND_RX,
#         smpplib.consts.SMPP_CLIENT_STATE_BOUND_TRX,
#     ]:
#         client.disconnect()


# ___________________________for tlv testing without segments put msg in message_payload___________________________
# # ⚡️ EVERYTHING is now safely inside the try block
# try:
#     print(f"Connecting to Squad Server at {SERVER_IP}...")
#     client.connect()
#     client.bind_transceiver(system_id="yukesh", password="yukesh")
#     print("✅ Successfully Bound")

#     print("\nPreparing MASSIVE SMS for splitting...")
#     # msg = "⚡️ SQUAD ALERT: This is a test message to demonstrate automatic splitting of long messages with emojis!😊"

#     # ____________________tlv__________________
#     base_sentence = (
#         "⚡️ SQUAD ALERT: Testing the giant 0x0424 message_payload TLV parameter! 😊 "
#     )
#     msg = base_sentence * 2  # ~750 characters!
#     raw_bytes = msg.encode("utf-16-be")
#     chunk_size = 140  # Max payload size for UCS-2 when there is no UDH header

#     # Slice the bytes into chunks of 140
#     parts = [
#         raw_bytes[i : i + chunk_size] for i in range(0, len(raw_bytes), chunk_size)
#     ]
#     total_parts = len(parts)
#     # ____________________tlv__________________

#     # base_sentence = "There is an awareness program today, please call 9801234567. "
#     # msg = "😊 " + (base_sentence * 12)
#     # 1. ⚡️ THE SPLITTER: Let the library calculate the chunks, the UDH, and the encoding!
#     # parts, encoding_flag, msg_type_flag = smpplib.gsm.make_parts(msg)   #for udh
#     sar_reference_number = secrets.randbelow(65535)
#     # print("parts", parts)
#     # print("encoding_flag", encoding_flag)
#     # print("msg_type_flag", msg_type_flag)
#     # print(
#     #     f"📦 Message automatically split into {len(parts)} parts! Firing them at the server..."
#     # )
#     client.send_message(
#         source_addr_ton=5,
#         source_addr_npi=0,
#         source_addr="SQUAD",
#         dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
#         dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
#         destination_addr="+573213389839",
#         # 1. ⚡️ CRITICAL: Leave the standard short_message completely empty!
#         short_message=b"",
#         data_coding=8,
#         esm_class=0,  # Normal message (no UDH bits needed)
#         registered_delivery=True,
#         # 2. ⚡️ THE MAGIC TLV: Stuff the entire giant payload in here
#         message_payload=raw_bytes,
#     )
#     # 2. ⚡️ THE LOOP: Fire each part over the network separately
#     # for i, part in enumerate(parts):
#     #     print(f"   -> Firing Part {i+1}...")
#     #     # client.send_message(
#     #     #     source_addr_ton=5,
#     #     #     source_addr_npi=0,
#     #     #     source_addr="SQUAD",
#     #     #     dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
#     #     #     dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
#     #     #     destination_addr="+573213389839",
#     #     #     # destination_addr="+9779851047370",
#     #     #     # Send the specific binary chunk (which now has the UDH prepended to it)
#     #     #     short_message=part,
#     #     #     # The library automatically figured out we need UCS-2 (8) because of the emojis
#     #     #     data_coding=encoding_flag,
#     #     #     # The library automatically turns on the 0x40 bit to tell your server it's multipart
#     #     #     esm_class=msg_type_flag,
#     #     #     registered_delivery=True,
#     #     # )
#     #     client.send_message(
#     #         source_addr_ton=5,
#     #         source_addr_npi=0,
#     #         source_addr="SQUAD",
#     #         dest_addr_ton=smpplib.consts.SMPP_TON_INTL,
#     #         dest_addr_npi=smpplib.consts.SMPP_NPI_ISDN,
#     #         destination_addr="+573213389839",
#     #         # The clean, UDH-free text bytes
#     #         short_message=part,
#     #         # We are using emojis, so force UCS-2
#     #         data_coding=8,
#     #         # ⚡️ CRITICAL: Set to 0! Do NOT use 0x40 because there is no UDH inside the payload
#     #         esm_class=0,
#     #         registered_delivery=True,
#     #         # ⚡️ THE SAR TLVS (Optional Parameters)
#     #         sar_msg_ref_num=sar_reference_number,
#     #         sar_total_segments=total_parts,
#     #         sar_segment_seqnum=i + 1,
#     #     )

#     # Listen for all the responses
#     client.listen()

# except smpplib.exceptions.PDUError as e:
#     # This catches ANY strict protocol error (Bind 13/15, or Submit 11)
#     status_code = (
#         e.args[1] if len(e.args) >= 2 and isinstance(e.args[1], int) else "Unknown"
#     )

#     print("\n⚠️ SQUAD SERVER REJECTED REQUEST")
#     if status_code == 12:
#         print("❌ REASON: Invalid Destination Number")
#     elif status_code == 13:
#         print("❌ REASON: IP Address Not Whitelisted (Or Invalid System ID)")
#     elif status_code == 15:
#         print("❌ REASON: Invalid Password")
#     else:
#         print(f"❌ PROTOCOL REASON: Status Code {status_code}")

#     sys.exit(1)  # Stop the script safely

# except Exception as e:
#     print(f"\n❌ CRITICAL ERROR: {e}")
#     sys.exit(1)

# finally:
#     print("\nDisconnecting...")
#     # Safe disconnect check
#     if hasattr(client, "state") and client.state in [
#         smpplib.consts.SMPP_CLIENT_STATE_BOUND_TX,
#         smpplib.consts.SMPP_CLIENT_STATE_BOUND_RX,
#         smpplib.consts.SMPP_CLIENT_STATE_BOUND_TRX,
#     ]:
#         client.disconnect()
