from email import errors
import os
from time import time
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

from squadServices import models
from squadServices.models.country import Country
from squadServices.models.mappingSetup.mappingSetup import MappingSetup
from squadServices.models.operators.operators import Operators
from squadServices.models.rateManagementModel.vendorRate import VendorRate
from squadServices.serializer.roleManagementSerializer.vendorRateSerializer import (
    VendorRateImportSerializer,
)
from dateutil import parser
import logging
import re  # Make sure this is at the top of your file!

User = get_user_model()
from django.conf import settings
from squadServices.models.company import Company
from squadServices.models.email import EmailHost
import uuid
from django.db.models import Q

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
