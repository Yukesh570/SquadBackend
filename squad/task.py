from celery import shared_task
from django.core.mail import send_mail
from django.core.mail import get_connection, EmailMessage

from squadServices.models.email import EmailHost

@shared_task
def sendEmailTask(subject, message, fromEmail, recipientList, emailHostId):
    try:
        emailHost=EmailHost.objects.get(pk=emailHostId)
    except EmailHost.DoesNotExist:
        return
    connection = get_connection(
        host=emailHost.smtpHost,
        port=emailHost.smtpPort,
        username=emailHost.smtpUser,
        password=emailHost.smtpPassword,
        use_tls=emailHost.useTls,
    )
    email =EmailMessage(
        subject=subject,
        body=message,
        from_email=fromEmail,
        to=recipientList,
        connection=connection
    )

    email.send()

