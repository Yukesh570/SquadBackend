# myapp/models.py
from django.conf import settings
from django.db import models

from squadServices.models.clientModel.client import Client
from squadServices.models.connectivityModel.smpp import SMPP
from squadServices.models.connectivityModel.verdor import Vendor


class SMSMessage(models.Model):
    STATUS_CHOICES = (
        ("queued", "Queued"),
        ("sent", "Sent"),
        ("failed", "Failed"),
        ("delivered", "Delivered"),
    )

    destination = models.CharField(max_length=20)
    text = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    message_id = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )  # ID from SMSC
    client = models.ForeignKey(
        Client,
        null=True,
        on_delete=models.CASCADE,
        related_name="clientSMSMessage",
    )
    vendor = models.ForeignKey(
        Vendor,
        null=True,
        on_delete=models.CASCADE,
        related_name="vendorSMSMessage",
    )
    smpp = models.ForeignKey(
        SMPP,
        on_delete=models.DO_NOTHING,
        related_name="smsMessageSmpp",
        null=True,
        blank=True,
    )
    systemId = models.CharField(
        max_length=255, blank=True, null=True
    )  # Vendor system ID

    encoding = models.CharField(max_length=255, blank=True, null=True)
    segmentNumber = models.CharField(max_length=255, blank=True, null=True)
    characterCount = models.CharField(max_length=255, blank=True, null=True)
    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="smpp_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="smpp_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.destination} - {self.status}"

    class Meta:
        ordering = ["-updatedAt"]
        # Force Django to look for the lowercase table in Postgres
        # while keeping the app label as 'squadServices'
        db_table = "squadServices_smsmessage"
