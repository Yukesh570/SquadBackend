import smpplib.gsm
import smpplib.client
import smpplib.consts
import time
import threading  # ⚡️ IMPORT THREADING

# --- Configuration ---
SERVER_IP = "192.168.1.146"
SYSTEM_ID = "RishiMahat5930"
PASSWORD = "Rish3402"
DEST_NUMBER = "573213389839"

LONG_TEXT = "This is a very long message designed to test the SMPP server reassembly logic.multiple segments. Part 1, Part 2, and maybe Part 3 should all arrive and be joined!"


def handle_deliver_sm(pdu):
    msg = pdu.short_message.decode("ascii", errors="ignore")
    status = "SUCCESS" if "stat:DELIVRD" in msg else "REJECTED"
    # print(f"DEBUG | DLR Received | Type: {status} | Content: {msg[:60]}...")
    return 0


def create_bound_client(port):
    client = smpplib.client.Client(SERVER_IP, port)
    client.set_message_received_handler(handle_deliver_sm)
    client.connect()
    client.bind_transceiver(system_id=SYSTEM_ID, password=PASSWORD)
    print(f"Connected and Bound to Port {port}")
    return client


def send_messages(client, count, start_index):
    for i in range(start_index, start_index + count):
        msg_content = f"PortTest #{i}" if i % 10 != 0 else LONG_TEXT

        parts, encoding, esm_class = smpplib.gsm.make_parts(msg_content)
        for part in parts:
            client.send_message(
                source_addr="SQUAD",
                destination_addr=DEST_NUMBER,
                short_message=part,
                data_coding=encoding,
                esm_class=esm_class,
                registered_delivery=True,
            )


# ⚡️ NEW: Background worker to constantly read incoming receipts
def listen_in_background(client):
    try:
        client.listen(ignore_error_codes=[0])
    except Exception as e:
        pass


def run_dual_test():
    client_2776 = create_bound_client(2776)
    client_2777 = create_bound_client(2777)

    # ⚡️ Start the background listeners BEFORE we start blasting messages!
    # This prevents the Windows TCP buffer from overflowing.
    t1 = threading.Thread(target=listen_in_background, args=(client_2776,), daemon=True)
    t2 = threading.Thread(target=listen_in_background, args=(client_2777,), daemon=True)
    t1.start()
    t2.start()

    print(f"\n--- STARTING BURST ---")
    start_time = time.time()

    print("Sending 400 messages to Port 2777...")
    send_messages(client_2777, 200, 1)

    print("Sending 400 messages to Port 2776...")
    send_messages(client_2776, 200, 401)

    duration = time.time() - start_time
    print(f"Burst complete in {duration:.2f} seconds.")

    # Just sleep and let the background threads catch the remaining DLRs
    print("Waiting 15 seconds for final background DLRs to arrive...")
    time.sleep(15)

    for c in [client_2776, client_2777]:
        try:
            c.unbind()
            c.disconnect()
        except:
            pass


if __name__ == "__main__":
    run_dual_test()
