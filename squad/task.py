from email import errors
import io
import os
from time import time
from urllib.parse import urljoin
from celery import shared_task
from django.apps import apps
from django.core.mail import send_mail
from django.core.mail import get_connection, EmailMessage
from django.core.mail import EmailMultiAlternatives
from datetime import datetime
import csv
import redis
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status
from rest_framework.response import Response
import json
from django.core.files.storage import default_storage
from squadServices import models
from squadServices.models.campaign import CampaignContact
from squadServices.models.connectivityModel.verdor import Vendor
from squadServices.models.country import Country
from squadServices.models.finanace.invoice import ClientInvoice, VendorInvoice
from squadServices.models.finanace.invoiceSetup import InvoiceSetup
from squadServices.models.mappingSetup.mappingSetup import MappingSetup
from squadServices.models.operators.operators import Operators
from squadServices.models.rateManagementModel.vendorRate import VendorRate
from squadServices.models.transaction.transaction import (
    TransactionType,
    VendorTransaction,
)
from squadServices.serializer.roleManagementSerializer.vendorRateSerializer import (
    VendorRateImportSerializer,
)
from django.db import transaction
from io import BytesIO
from django.template.loader import get_template
from django.core.files.base import ContentFile
from xhtml2pdf import pisa
from num2words import num2words
from dateutil import parser
import logging
import re  # Make sure this is at the top of your file!

User = get_user_model()
from django.conf import settings
from squadServices.models.company import Company
from squadServices.models.email import EmailHost
import uuid
from django.db.models import Q


import math
import openpyxl
from django.utils import timezone
from squadServices.models import Campaign
from squadServices.models.smpp.smppSMS import SMSMessage
from squadServices.models.detailedReport.detailedReport import DetailedSMSReport
from squadServices.helper.checkNumber import clean_phone_number
from squadServices.helper.smsSplitter import create_message_parts

logger = logging.getLogger(__name__)

redis_client = redis.StrictRedis.from_url(os.getenv("CELERY_RESULT_BACKEND"))


@shared_task
def sendEmailTask(
    subject, message, fromEmail, recipientList, emailHostId, attachments=None
):
    try:
        emailHost = EmailHost.objects.get(pk=emailHostId, isDeleted=False)
    except EmailHost.DoesNotExist:
        return
    if emailHost.security == "TLS":
        connection = get_connection(
            host=emailHost.smtpHost,
            port=emailHost.smtpPort,
            username=emailHost.smtpUser,
            password=emailHost.smtpPassword,
            use_tls=True,
        )
    elif emailHost.security == "SSL":
        connection = get_connection(
            host=emailHost.smtpHost,
            port=emailHost.smtpPort,
            username=emailHost.smtpUser,
            password=emailHost.smtpPassword,
            use_ssl=True,
        )
    email = EmailMultiAlternatives(
        subject=subject + "\u200b",
        body=message,
        from_email=fromEmail,
        to=recipientList,
        connection=connection,
    )

    email.content_subtype = "html"  # <-- tell Django this is HTML
    if attachments:
        for att in attachments:
            """
            att must contain:
            {
                "name": "invoice.pdf",
                "content": "<BASE64_STRING>",
                "type": "application/pdf"
            }
            """
            import base64

            file_name = att["name"]
            file_content = base64.b64decode(att["content"])
            mime_type = att.get("type", "application/octet-stream")

            email.attach(file_name, file_content, mime_type)

    email.send()


@shared_task()
def export_model_csv(model_name: str, filters=None, fields=None, module=None):
    """
    Generate CSV for any model asynchronously.
    """
    print(model_name, filters, fields, module)

    task_id = export_model_csv.request.id  # unique task ID

    # Resolve model
    try:
        Model = apps.get_model(model_name)
    except LookupError:
        redis_client.set(task_id, "error:Model not found")

        return f"Model {model_name} not found"

    # Generate unique filename
    filename = (
        f"{module or Model._meta.model_name}_{uuid.uuid4().hex}_{int(time())}.csv"
    )
    export_dir = os.path.join(settings.MEDIA_ROOT, "exports")
    os.makedirs(export_dir, exist_ok=True)
    filepath = os.path.join(export_dir, filename)

    # Base queryset
    queryset = (
        Model.objects.filter(isDeleted=False)
        if hasattr(Model, "isDeleted")
        else Model.objects.all()
    )

    # Apply filters
    if filters:
        transformed_filters = {f"{k}__icontains": v for k, v in filters.items()}
        queryset = queryset.filter(**transformed_filters)
    total = queryset.count()
    if total == 0:
        redis_client.set(task_id, "100")
        redis_client.set(f"{task_id}_result", filename)
        return filename
    # Determine fields
    if fields is None:
        fields = [field.name for field in Model._meta.fields]
    processed = 0

    # Write CSV
    # Write CSV
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fields)

        for obj in queryset.iterator(chunk_size=2000):
            processed += 1

            row = []
            for field_name in fields:
                val = getattr(obj, field_name, None)

                # Safely extract the 'name' if it's a Foreign Key
                if val is not None and hasattr(val, "name"):
                    val = val.name
                elif val is None:
                    val = ""
                else:
                    val = str(val)

                # THE EXCEL HACK:
                # If the string is only digits and commas (like "734,901"),
                # wrap it in an Excel formula so Excel doesn't delete the comma.
                if re.fullmatch(r"[\d,]+", val) and "," in val:
                    val = f'="{val}"'

                row.append(val)

            writer.writerow(row)

            # Update Redis
            progress = int((processed / total) * 100)
            redis_client.set(task_id, str(progress))
    # Schedule deletion after 5 minutes
    deleteForLater.apply_async(args=[filepath], countdown=300)
    redis_client.set(task_id, "100")
    redis_client.set(f"{task_id}_result", filename)
    return filename


@shared_task
def deleteForLater(filepath):
    """Delete exported CSV file safely."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Failed to delete {filepath}: {e}")


@shared_task(bind=True)
def import_vendor_rate_task(self, filepath, user_id, task_id, mapping_id):
    redis_client.set(task_id, "0")

    created = 0
    failed = []

    mapping = MappingSetup.objects.filter(id=mapping_id).first()
    if not mapping:
        redis_client.set(task_id, "error: Mapping not found")
        if os.path.exists(filepath):
            os.remove(filepath)
        return

    # Normalize header_map once
    header_map = {
        mapping.ratePlan.lower().strip(): "ratePlan",
        mapping.country.lower().strip(): "country",
        mapping.countryCode.lower().strip(): "countryCode",
        mapping.timeZone.lower().strip(): "timeZone",
        mapping.network.lower().strip(): "network",
        mapping.MCC.lower().strip(): "MCC",
        mapping.MNC.lower().strip(): "MNC",
        mapping.rate.lower().strip(): "rate",
        mapping.dateTime.lower().strip(): "dateTime",
    }

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            # Pre-map CSV header names -> model fields
            csv_header_map = {}
            for col in reader.fieldnames:
                normalized_col = col.lower().strip()
                logger.info(f"normalized_col={normalized_col}")
                logger.info(f"header_map={header_map}")

                if normalized_col in header_map:
                    csv_header_map[col] = header_map[normalized_col]

            rows = list(reader)
            total = len(rows)
            user = User.objects.get(id=user_id)
            print("=========!!!!====================")

            for index, row in enumerate(rows, start=1):

                mapped_row = {}

                # Use pre-mapped header mapping
                for col, val in row.items():
                    if col in csv_header_map:
                        mapped_row[csv_header_map[col]] = val

                # Clean numeric fields
                for key in ["MCC", "MNC", "rate", "countryCode"]:
                    if mapped_row.get(key) == "":
                        mapped_row[key] = None

                # Parse datetime
                if mapped_row.get("dateTime"):
                    try:
                        mapped_row["dateTime"] = parser.parse(mapped_row["dateTime"])
                    except:
                        failed.append({"row": index, "error": "Invalid dateTime"})
                        continue
                # Example before serializer.save()
                if VendorRate.objects.filter(
                    ratePlan=mapped_row.get("ratePlan"),
                ).exists():
                    failed.append({"row": index, "error": "Duplicate entry"})
                    continue

                serializer = VendorRateImportSerializer(data=mapped_row)

                if serializer.is_valid():
                    serializer.save(createdBy=user, updatedBy=user)
                    created += 1
                else:
                    failed.append({"row": index, "error": serializer.errors})

                # Update progress
                redis_client.set(task_id, str(int((index / total) * 100)))

    except Exception as e:
        redis_client.set(task_id, f"error:{str(e)}")
        return

    redis_client.set(task_id, "100")
    redis_client.set(
        f"{task_id}_result",
        json.dumps({"message": f"{total} rows processed", "errors": failed}),
    )

    if os.path.exists(filepath):
        os.remove(filepath)

    return "done"


@shared_task(bind=True)
def import_country_task(self, filepath, user_id, task_id):
    """
    Import countries from CSV.
    Expected CSV headers: name,countryCode,MCC
    """
    redis_client.set(task_id, "0")
    errors = []

    try:
        user = User.objects.filter(id=user_id).first()

        with open(filepath, newline="", encoding="utf-8") as csvfile:
            rows = list(csv.DictReader(csvfile))
            total = len(rows)

            if total == 0:
                redis_client.set(task_id, "100")
                redis_client.set(
                    f"{task_id}_result",
                    json.dumps({"message": "Empty CSV", "errors": []}),
                )
                return

            for index, row in enumerate(rows, start=1):
                name = row.get("name", "").strip()
                code = row.get("countryCode", "").strip()

                if not name or not code:
                    errors.append(
                        {"row": index, "error": "Missing name or countryCode"}
                    )
                    continue

                # Check if country already exists (by name or countryCode)
                if Country.objects.filter(Q(name=name), isDeleted=False).exists():
                    errors.append(
                        {
                            "row": index,
                            "error": f"Country '{name}'  already exists",
                        }
                    )
                    continue
                raw_mcc = str(row.get("MCC") or "0").strip()
                # 2. Remove commas and spaces
                # clean_mcc = raw_mcc.replace(",", "").strip()
                try:
                    Country.objects.create(
                        name=name,
                        countryCode=code,
                        MCC=raw_mcc,
                        createdBy=user,
                        updatedBy=user,
                        isDeleted=False,
                    )
                except Exception as e:
                    errors.append({"row": index, "error": str(e)})
                    continue

                # Update progress
                progress = int((index / total) * 100)
                redis_client.set(task_id, str(progress))

        # Mark complete
        redis_client.set(task_id, "100")
        redis_client.set(
            f"{task_id}_result",
            json.dumps({"message": f"{total} rows processed", "errors": errors}),
        )

        deleteForLater.apply_async(args=[filepath], countdown=100)

    except Exception as e:
        redis_client.set(task_id, f"error:{str(e)}")


@shared_task(bind=True)
def import_operator_task(self, filepath, user_id, task_id):
    """
    Import operators from CSV.
    Expected CSV headers: name,country,MNC
    """
    redis_client.set(task_id, "0")  # initial progress
    errors = []

    try:
        with open(filepath, newline="", encoding="utf-8") as csvfile:
            rows = list(csv.DictReader(csvfile))
            total = len(rows)
            user = User.objects.get(id=user_id)

            if total == 0:
                redis_client.set(task_id, "100")
                redis_client.set(
                    f"{task_id}_result",
                    json.dumps({"message": "Empty CSV", "errors": []}),
                )
                return

            for index, row in enumerate(rows, start=1):
                name = row.get("name", "").strip()
                country_name = row.get("country", "").strip()
                mnc = row.get("MNC")

                # Validate required fields
                if not name or not country_name:
                    errors.append({"row": index, "error": "Missing name or country"})
                    continue

                # Check if country exists
                country = Country.objects.filter(
                    name__iexact=country_name, isDeleted=False
                ).first()
                if not country:
                    errors.append(
                        {"row": index, "error": f"Country '{country_name}' not found"}
                    )
                    continue

                # Check if operator already exists
                if Operators.objects.filter(
                    name=name, country=country, isDeleted=False
                ).exists():
                    errors.append(
                        {
                            "row": index,
                            "error": f"Operator '{name}' for country '{country_name}' already exists",
                        }
                    )
                    continue

                try:
                    Operators.objects.create(
                        name=name,
                        country=country,
                        MNC=int(mnc) if mnc else 0,
                        createdBy=user,
                        updatedBy=user,
                        isDeleted=False,
                    )
                except Exception as e:
                    errors.append({"row": index, "error": str(e)})
                    continue

                # Update progress
                progress = int((index / total) * 100)
                redis_client.set(task_id, str(progress))

        # Mark complete
        redis_client.set(task_id, "100")
        redis_client.set(
            f"{task_id}_result",
            json.dumps({"message": f"{total} rows processed", "errors": errors}),
        )

        # Schedule file deletion
        deleteForLater.apply_async(args=[filepath], countdown=100)

    except Exception as e:
        redis_client.set(task_id, f"error:{str(e)}")


@shared_task
def generate_invoice_pdf_task(invoice_id, breakdown_data, tax_amount=0, base_url=""):
    """
    Background task to render HTML, convert to PDF, and save it to the database.
    """
    print(f"Generating PDF for invoice {invoice_id}")
    try:
        # 1. Fetch the invoice from the DB using the ID passed to Celery
        invoice_obj = ClientInvoice.objects.get(id=invoice_id)
    except ClientInvoice.DoesNotExist:
        print(f"Error: Invoice {invoice_id} not found.")
        return False
    client_company = invoice_obj.client.company
    setup_rules = InvoiceSetup.objects.filter(
        company=client_company, isDeleted=False
    ).first()
    business_entity = setup_rules.businessEntity if setup_rules else None

    if setup_rules and setup_rules.billingAddressOverride:
        final_address = setup_rules.billingAddressOverride
    else:
        final_address = client_company.address
    # 2. Calculate the final math
    total_amount = invoice_obj.totalAmount
    grand_total = float(total_amount) + float(tax_amount)

    # 3. Convert numbers to words
    amount_in_words = num2words(int(grand_total))
    # Prepare the logo URL safely
    logo_url = None
    if business_entity and business_entity.companyLogo:
        if base_url:
            # This safely combines "http://domain.com/" and "/media/logos/img.png"
            logo_url = urljoin(base_url, business_entity.companyLogo.url)
        else:
            logo_url = business_entity.companyLogo.url
    # 4. Prepare Context
    context = {
        "client": invoice_obj.client,
        "entity_name": (business_entity.companyName if business_entity else "N/A"),
        "entity_logo": logo_url,
        "entity_address": (
            business_entity.businessAddress if business_entity else "N/A"
        ),
        "entity_email": (business_entity.emailAddress if business_entity else "N/A"),
        "entity_phone": (business_entity.phone if business_entity else "N/A"),
        "client_name": client_company.name,
        "client_email": client_company.companyEmail,
        "client_currency": client_company.currency,
        "client_phone": client_company.phone,
        "client_address": final_address,
        "breakdown": breakdown_data,
        "total_amount": total_amount,
        "tax_amount": tax_amount,
        "grand_total": grand_total,
        "amount_in_words": amount_in_words,
        "bank_details": business_entity.bankAccountDetail,
    }

    # 5. Render HTML
    template = get_template("finance/invoice_pdf.html")
    html_string = template.render(context)

    # 6. Convert to PDF
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(BytesIO(html_string.encode("UTF-8")), dest=pdf_buffer)

    # 7. Save to the Database
    if not pisa_status.err:
        pdf_name = f"{invoice_obj.invoiceNumber}.pdf"
        invoice_obj.invoicePdf.save(pdf_name, ContentFile(pdf_buffer.getvalue()))
        invoice_obj.save()
        return f"Successfully generated PDF for Invoice {invoice_obj.invoiceNumber}"

    return f"Failed to generate PDF for Invoice {invoice_obj.invoiceNumber}"


@shared_task
def generate_vendorInvoice_pdf_task(
    invoice_id, breakdown_data, tax_amount=0, base_url=""
):
    """
    Background task to render HTML, convert to PDF, and save it to the database.
    """
    print(f"Generating PDF for invoice {invoice_id}")
    try:
        # 1. Fetch the invoice from the DB using the ID passed to Celery
        invoice_obj = VendorInvoice.objects.get(id=invoice_id)
    except VendorInvoice.DoesNotExist:
        print(f"Error: Invoice {invoice_id} not found.")
        return False
    vendor_company = invoice_obj.vendor.company
    setup_rules = InvoiceSetup.objects.filter(
        company=vendor_company, isDeleted=False
    ).first()
    business_entity = setup_rules.businessEntity if setup_rules else None

    if setup_rules and setup_rules.billingAddressOverride:
        final_address = setup_rules.billingAddressOverride
    else:
        final_address = vendor_company.address
    # 2. Calculate the final math
    total_amount = invoice_obj.totalAmount
    grand_total = float(total_amount) + float(tax_amount)

    # 3. Convert numbers to words
    amount_in_words = num2words(int(grand_total))
    logo_url = None
    if business_entity and business_entity.companyLogo:
        if base_url:
            # This safely combines "http://domain.com/" and "/media/logos/img.png"
            logo_url = urljoin(base_url, business_entity.companyLogo.url)
        else:
            logo_url = business_entity.companyLogo.url
    # 4. Prepare Context
    context = {
        "vendor": invoice_obj.vendor,
        "entity_name": (business_entity.companyName if business_entity else "N/A"),
        "entity_logo": logo_url,
        "entity_address": (
            business_entity.businessAddress if business_entity else "N/A"
        ),
        "entity_email": (business_entity.emailAddress if business_entity else "N/A"),
        "entity_phone": (business_entity.phone if business_entity else "N/A"),
        "vendor_name": vendor_company.name,
        "vendor_email": vendor_company.companyEmail,
        "vendor_currency": vendor_company.currency,
        "vendor_phone": vendor_company.phone,
        "vendor_address": final_address,
        "breakdown": breakdown_data,
        "total_amount": total_amount,
        "tax_amount": tax_amount,
        "grand_total": grand_total,
        "amount_in_words": amount_in_words,
        "bank_details": business_entity.bankAccountDetail if business_entity else "N/A",
    }

    # 5. Render HTML
    template = get_template("finance/vendorInvoice_pdf.html")
    html_string = template.render(context)

    # 6. Convert to PDF
    pdf_buffer = BytesIO()
    pisa_status = pisa.CreatePDF(BytesIO(html_string.encode("UTF-8")), dest=pdf_buffer)

    # 7. Save to the Database
    if not pisa_status.err:
        pdf_name = f"{invoice_obj.invoiceNumber}.pdf"
        invoice_obj.invoicePdf.save(pdf_name, ContentFile(pdf_buffer.getvalue()))
        invoice_obj.save()
        return f"Successfully generated PDF for Invoice {invoice_obj.invoiceNumber}"

    return f"Failed to generate PDF for Invoice {invoice_obj.invoiceNumber}"


def is_valid_contact(contact):
    return contact.isdigit() and 7 <= len(contact) <= 15


# Helper function to calculate SMS parts
def get_encoding_and_segments(text):
    gsm7_basic = "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
    gsm7_ext = "^{}\\[~]|€"
    encoding = "GSM-7"
    for char in text:
        if char not in gsm7_basic and char not in gsm7_ext:
            encoding = "UCS-2"
            break
    length = len(text)
    if encoding == "GSM-7":
        segments = 1 if length <= 160 else math.ceil(length / 153)
    else:
        segments = 1 if length <= 70 else math.ceil(length / 67)
    return encoding, segments, length


@shared_task
def process_campaign_contacts_task(
    campaign_id, file_path, contacts_string, user_id, message_text, vendor_id
):
    """
    Background worker to parse contacts, save them to the Campaign,
    and queue them up for the Vendor SMPP server.
    """
    createdContacts = []
    invalidContacts = []
    duplicateInInput = []
    seenInputs = set()

    try:
        campaign = Campaign.objects.get(id=campaign_id)
        user = User.objects.get(id=user_id)

        # ==========================================
        # 1. PARSE UPLOADED FILE (If exists)
        # ==========================================
        if file_path and default_storage.exists(file_path):
            file_name = file_path.lower()
            file_obj = default_storage.open(file_path)

            if file_name.endswith(".csv"):
                try:
                    decodedFile = file_obj.read().decode("utf-8")
                except UnicodeDecodeError:
                    file_obj.seek(0)
                    decodedFile = file_obj.read().decode("latin1")

                ioString = io.StringIO(decodedFile)
                reader = csv.DictReader(ioString)
                for row in reader:
                    row_lower = {k.lower(): v for k, v in row.items()}
                    contact = row_lower.get("contact", "").strip()
                    if contact and contact in seenInputs:
                        duplicateInInput.append(contact)
                    elif contact:
                        seenInputs.add(contact)
                        if is_valid_contact(contact):
                            createdContacts.append(
                                CampaignContact(
                                    campaign=campaign, contactNumber=contact
                                )
                            )
                        else:
                            invalidContacts.append(contact)

            elif file_name.endswith(".xlsx"):
                wb = openpyxl.load_workbook(file_obj)
                ws = wb.active
                headers = [
                    str(cell.value).lower()
                    for cell in next(ws.iter_rows(min_row=1, max_row=1))
                ]
                contact_idx = headers.index("contact") if "contact" in headers else None

                if contact_idx is not None:
                    for row in ws.iter_rows(min_row=2):
                        contact = (
                            str(row[contact_idx].value).strip()
                            if row[contact_idx].value
                            else ""
                        )
                        if contact and contact in seenInputs:
                            duplicateInInput.append(contact)
                        elif contact:
                            seenInputs.add(contact)
                            if is_valid_contact(contact):
                                createdContacts.append(
                                    CampaignContact(
                                        campaign=campaign, contactNumber=contact
                                    )
                                )
                            else:
                                invalidContacts.append(contact)

        # ==========================================
        # 2. PARSE MANUAL TEXT INPUT (If exists)
        # ==========================================
        if contacts_string:
            print("666666666666666666666666666666666666666666666")
            contacts = [c.strip() for c in contacts_string.split(",") if c.strip()]
            print("666666666666666666666666666666666666666666666", contacts)

            for contact in contacts:
                if contact in seenInputs:
                    print("666666666666666666666666666666666666666666666", contact)

                    duplicateInInput.append(contact)
                    print(
                        "666666666666666666666666666666666666666666666",
                        duplicateInInput,
                    )

                else:
                    seenInputs.add(contact)
                    print("111111111111111111111111111111111111111111111111", contact)

                    print("111111111111111111111111111111111111111111111111", contact)

                    createdContacts.append(
                        CampaignContact(campaign=campaign, contactNumber=contact)
                    )

        # ==========================================
        # 3. SAVE TO DATABASE & QUEUE SMS
        # ==========================================
        if createdContacts:
            print("55555555555555", contact)

            CampaignContact.objects.bulk_create(createdContacts)

            # Setup Vendor & Encoding logic
            encoding_type, total_segments, total_chars = get_encoding_and_segments(
                message_text
            )
            default_vendor = (
                Vendor.objects.filter(id=vendor_id).first() or Vendor.objects.first()
            )
            vendorRatePerSegment = VendorRate.objects.filter(
                ratePlan=default_vendor.ratePlanName
            ).first()
            print(
                "55555555555555",
                default_vendor,
                vendorRatePerSegment,
                encoding_type,
                total_segments,
            )
            total_vendor_cost = vendorRatePerSegment.rate * total_segments
            print("wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww")
            # Loop to generate SMPP Messages
            for contact_obj in createdContacts:
                # Clean it just to be safe for the SMPP server
                destination_addr = clean_phone_number(
                    contact_obj.contactNumber
                ).replace("+", "")
                print(
                    f"Queuing SMS to {destination_addr} with encoding {encoding_type} and {total_segments} segments"
                )
                unique_msg_id = str(uuid.uuid4())  # Add 'await'

                with transaction.atomic():
                    # A. Lock the Vendor's Parent Company to prevent race conditions
                    locked_vendor_company = (
                        type(default_vendor.company)
                        .objects.select_for_update()
                        .get(id=default_vendor.company.id)
                    )

                    # B. Update the Balance
                    locked_vendor_company.usedVendorCredit += total_vendor_cost
                    locked_vendor_company.save(update_fields=["usedVendorCredit"])
                    parent_msg = SMSMessage.objects.create(
                        destination=destination_addr,
                        message_id=unique_msg_id,  # Add 'message_id'
                        text=message_text,
                        encoding=encoding_type,
                        segmentNumber=total_segments,
                        characterCount=total_chars,
                        status="queued",
                        vendor=default_vendor,
                        smpp=default_vendor.smpp,
                        client=None,
                        createdBy=user,
                        sendClientDlr=False,
                        queued_at=timezone.now(),
                    )
                    VendorTransaction.objects.create(
                        vendor=default_vendor,
                        message=parent_msg,
                        transactionType=TransactionType.DEDUCTION,
                        segments=total_segments,
                        ratePerSegment=vendorRatePerSegment.rate,
                        amount=total_vendor_cost,
                        balanceSpent=locked_vendor_company.usedVendorCredit,
                        description=f"System Campaign - Routing charge for SMS {parent_msg.message_id}",
                    )

                create_message_parts(parent_msg, message_text)

                DetailedSMSReport.objects.create(
                    message=parent_msg,
                    text_message_id=parent_msg.message_id or f"queued-{parent_msg.id}",
                    text=parent_msg.text,
                    part_total=total_segments,
                    client="SYSTEM_CAMPAIGN",
                    clientRate=0.00,
                    client_charge=0.00,
                    vendor=default_vendor.profileName if default_vendor else "Unknown",
                    vendorRate=vendorRatePerSegment.rate,
                    vendor_charge=total_vendor_cost,
                    submitStatus="QUEUED",
                    request_time=parent_msg.createdAt,
                    destination=parent_msg.destination,
                )

    except Exception as e:
        print(f"🔥 Task Failed for Campaign {campaign_id}: {str(e)}")

    finally:
        # CLEANUP: Delete the temp file so your server doesn't bloat
        if file_path and default_storage.exists(file_path):
            try:
                if "file_obj" in locals():
                    file_obj.close()
            except Exception:
                pass
            default_storage.delete(file_path)
