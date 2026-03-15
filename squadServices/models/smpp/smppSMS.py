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
        return f"{self.destination}"

    class Meta:
        ordering = ["-updatedAt"]
        # Force Django to look for the lowercase table in Postgres
        # while keeping the app label as 'squadServices'
        db_table = "squadServices_smsmessage"


class SMSMessagePart(models.Model):
    STATUS_CHOICES = (
        ("QUEUED", "Queued"),
        ("DELIVERED", "Delivered"),  # <--- Add this!
        ("SUBMITTED", "Submitted"),
        ("FAILED", "Failed"),
    )

    # Links back to the parent message
    message = models.ForeignKey(
        "SMSMessage", related_name="parts", on_delete=models.CASCADE
    )

    # Tracking the pieces
    part_no = models.IntegerField()
    part_total = models.IntegerField()
    udh_ref = models.IntegerField()

    # esm_class = 0x40 tells the vendor "The first 6 bytes are routing instructions!"
    esm_class = models.IntegerField(default=0x00)

    # The actual payload (UDH bytes + Text chunk bytes)
    short_message = models.BinaryField()

    # State tracking
    submit_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="QUEUED"
    )
    vendor_msg_id = models.CharField(max_length=100, null=True, blank=True)
    vendor_submit_status = models.IntegerField(null=True, blank=True)

    submit_attempts = models.IntegerField(default=0)
    last_submit_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Msg {self.message.id} - Part {self.part_no}/{self.part_total}"
