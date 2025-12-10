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

from squadServices.models.mappingSetup.mappingSetup import MappingSetup
from squadServices.serializer.roleManagementSerializer.vendorRateSerializer import (
    VendorRateImportSerializer,
)
from dateutil import parser

User = get_user_model()
from django.conf import settings
from squadServices.models.company import Company
from squadServices.models.email import EmailHost
import uuid

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


@shared_task
def export_model_csv(model_name: str, filters=None, fields=None, module=None):
    """
    Generate CSV for any model asynchronously.
    """
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
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        for obj in queryset.iterator(chunk_size=2000):
            processed += 1

            row = [
                getattr(obj, f, getattr(getattr(obj, f, ""), "name", ""))
                for f in fields
            ]
            writer.writerow(row)
            progress = int((processed / total) * 100)
            redis_client.set(task_id, progress)

    # Schedule deletion after 5 minutes
    delete_exported_file_later.apply_async(args=[filepath], countdown=300)
    redis_client.set(task_id, "100")
    redis_client.set(f"{task_id}_result", filename)
    return filename


@shared_task
def delete_exported_file_later(filepath):
    """Delete exported CSV file safely."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Failed to delete {filepath}: {e}")


@shared_task(bind=True)
def import_vendor_rate_task(self, filepath, user_id, task_id, mapping_id):
    redis_client.set(task_id, "0")
    print("import_vendor_rate_task", filepath, user_id, task_id, mapping_id)
    print("=============================")
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
                print("normalized_col", normalized_col)
                print("header_map", header_map)
                if normalized_col in header_map:
                    csv_header_map[col] = header_map[normalized_col]

            rows = list(reader)
            total = len(rows)
            user = User.objects.get(id=user_id)

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
    redis_client.set(f"{task_id}_result", str({"created": created, "failed": failed}))

    if os.path.exists(filepath):
        os.remove(filepath)

    return "done"
