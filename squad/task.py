from celery import shared_task
from django.core.mail import send_mail
from django.core.mail import get_connection, EmailMessage
from django.core.mail import EmailMultiAlternatives

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
    # message = """
    # <p>Dear {member},</p>
    # <p>Merchant TouristSavers from {merchantname} in your TouristSaver account are going to expire on {merchantpiinkexpirydate}.</p>
    # """.format(
    #     member="rewrew",
    #     merchantname="merchantname",
    #     merchantpiinkexpirydate="merchantpiinkexpirydate",
    # )
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
