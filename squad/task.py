import os
from time import time
from celery import shared_task
from django.apps import apps
from django.core.mail import send_mail
from django.core.mail import get_connection, EmailMessage
from django.core.mail import EmailMultiAlternatives
from datetime import datetime
import csv
from django.conf import settings
from squadServices.models.company import Company
from squadServices.models.email import EmailHost
import uuid


@shared_task
def sendEmailTask(subject, message, fromEmail, recipientList, emailHostId,attachments=None):
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
        subject = subject + "\u200B",
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
    # Resolve model
    try:
        Model = apps.get_model(model_name)
    except LookupError:
        return f"Model {model_name} not found"

    # Generate unique filename
    filename = f"{module or Model._meta.model_name}_{uuid.uuid4().hex}_{int(time())}.csv"
    export_dir = os.path.join(settings.MEDIA_ROOT, "exports")
    os.makedirs(export_dir, exist_ok=True)
    filepath = os.path.join(export_dir, filename)

    # Base queryset
    queryset = Model.objects.filter(isDeleted=False) if hasattr(Model, 'isDeleted') else Model.objects.all()

    # Apply filters
    if filters:
        transformed_filters = {f"{k}__icontains": v for k, v in filters.items()}
        queryset = queryset.filter(**transformed_filters)

    # Determine fields
    if fields is None:
        fields = [field.name for field in Model._meta.fields]

    # Write CSV
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        for obj in queryset.iterator(chunk_size=2000):
            row = [getattr(obj, f, getattr(getattr(obj, f, ""), "name", "")) for f in fields]
            writer.writerow(row)

    # Schedule deletion after 5 minutes
    delete_exported_file_later.apply_async(args=[filepath], countdown=300)

    return filename


@shared_task
def delete_exported_file_later(filepath):
    """Delete exported CSV file safely."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
    except Exception as e:
        print(f"Failed to delete {filepath}: {e}")