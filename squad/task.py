import os
from time import time
from celery import shared_task
from django.core.mail import send_mail
from django.core.mail import get_connection, EmailMessage
from django.core.mail import EmailMultiAlternatives
from datetime import datetime
import csv
from django.conf import settings
from squadServices.models.company import Company
from squadServices.models.email import EmailHost


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
def delete_exported_file_later(filepath):
    """Delete an exported CSV file after some delay."""
    import time, os
    time.sleep(120)

    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            print("Deleted CSV:", filepath)
    except Exception as e:
        print("Error deleting CSV:", e)


@shared_task
def export_companies_csv(filters=None):
    """
    Generate CSV using Celery.
    filters will be used to filter the queryset exactly like DRF.
    """

    # Generate filename
    filename = f"companies_{int(time())}.csv"
    export_dir = os.path.join(settings.MEDIA_ROOT, "exports")
    os.makedirs(export_dir, exist_ok=True)

    filepath = os.path.join(export_dir, filename)

    # Base queryset
    queryset = Company.objects.all(isDeleted=False)

    # Apply filters if passed
    if filters:
        transformed_filters = {
        f"{k}__icontains": v for k, v in filters.items()
        }
        queryset = queryset.filter(**transformed_filters)

    # Select related for speed
    queryset = queryset.select_related(
        'category', 'status', 'currency', 'timeZone', 'businessEntity'
    )

    # Write CSV
    with open(filepath, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)

        # Header
        writer.writerow([
            'ID', 'Name', 'Short Name', 'Phone', 'Company Email', 
            'Category', 'Status', 'Currency', 'Time Zone',
            'Business Entity', 'Customer Credit Limit',
            'Vendor Credit Limit', 'Address', 'Blocked'
        ])

        # Iterator = memory safe
        for obj in queryset.iterator(chunk_size=2000):
            writer.writerow([
                obj.id,
                obj.name,
                obj.shortName,
                obj.phone,
                obj.companyEmail,
                obj.category.name if obj.category else "",
                obj.status.name if obj.status else "",
                obj.currency.name if obj.currency else "",
                obj.timeZone.name if obj.timeZone else "",
                obj.businessEntity.name if obj.businessEntity else "",
                obj.customerCreditLimit,
                obj.vendorCreditLimit,
                obj.address,
                obj.companyBlocked
            ])
    delete_exported_file_later.delay(filepath)

    # Return file path (served via MEDIA_URL)
    return filename