import random
import struct

from squadServices.models.smpp.smppSMS import SMSMessagePart


def create_message_parts(sms_message_obj, text):
    """
    Takes a saved SMSMessage object and its text, chunks it,
    prepends the UDH, and saves the parts to the database.
    """

    # 1. Determine Encoding & Chunk Sizes
    # If there are emojis/special chars, we use UCS-2 (utf-16be)
    if any(ord(c) > 127 for c in text):
        encoding_used = "utf-16be"  # <--- Track encoding for decoding later
        text_bytes = text.encode(encoding_used)
        max_single = 140  # Max bytes for a single UCS-2 SMS
        max_multi = 134  # Max bytes per chunk when splitting UCS-2
    else:
        encoding_used = "latin1"  # <--- Track encoding for decoding later
        text_bytes = text.encode(encoding_used, errors="ignore")
        max_single = 160  # Max bytes for a single GSM/Latin1 SMS
        max_multi = 153  # Max bytes per chunk when splitting GSM/Latin1

    parts_created = []

    # 2. Handle Short Messages (No splitting needed)
    if len(text_bytes) <= max_single:
        part = SMSMessagePart.objects.create(
            message=sms_message_obj,
            text=text,  # <--- SAVE FULL TEXT HERE
            part_no=1,
            part_total=1,
            udh_ref=0,
            esm_class=0x00,  # 0x00 = Standard SMS, no header
            short_message=text_bytes,
        )
        parts_created.append(part)
        return parts_created

    # 3. Handle Long Messages (Amir's UDH Magic)
    # Generate a random 8-bit reference number (1-255) to link the parts
    udh_ref = random.randint(1, 255)

    # Slice the byte array into chunks
    chunks = [
        text_bytes[i : i + max_multi] for i in range(0, len(text_bytes), max_multi)
    ]
    total_parts = len(chunks)

    for idx, chunk in enumerate(chunks):
        part_no = idx + 1

        # Pack the 6-byte UDH: 05 00 03 <ref> <total> <seq>
        # '!BBBBBB' tells Python to pack 6 unsigned bytes strictly
        udh = struct.pack("!BBBBBB", 0x05, 0x00, 0x03, udh_ref, total_parts, part_no)

        # Combine the header + the text chunk
        full_payload = udh + chunk
        decoded_chunk_text = chunk.decode(encoding_used, errors="ignore")
        part = SMSMessagePart.objects.create(
            message=sms_message_obj,
            text=decoded_chunk_text,  # <--- SAVE CHUNK TEXT HERE
            part_no=part_no,
            part_total=total_parts,
            udh_ref=udh_ref,
            esm_class=0x40,  # 0x40 = UDHI flag (Tells vendor to read the header!)
            short_message=full_payload,
        )
        parts_created.append(part)

    return parts_created
