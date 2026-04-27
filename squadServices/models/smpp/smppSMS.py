# myapp/models.py
from django.conf import settings
from django.db import models

from squadServices.models.clientModel.client import Client
from squadServices.models.connectivityModel.smpp import SMPP
from squadServices.models.connectivityModel.verdor import Vendor

from django.db import models
from django.utils import timezone
from django.db.models import JSONField  # Use this for storing raw network data

import uuid


class SMSMessage(models.Model):
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("queued", "Queued"),
        ("submitted", "Submitted"),
        ("failed", "Failed"),
        ("delivered", "Delivered"),
        # Added based on our previous logic
    )
    external_id = models.UUIDField(
        default=uuid.uuid4, editable=False, unique=True, db_index=True, null=True
    )
    destination = models.CharField(max_length=20)
    text = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="queued")
    message_id = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )  # ID from SMSC
    sendClientDlr = models.BooleanField(
        default=False,
        help_text="True if the client requested a DLR AND their account is allowed to receive them.",
    )
    clientDlrPushed = models.BooleanField(
        default=False,
        help_text="True if we have successfully forwarded the final DLR back to the client.",
    )

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

    encoding = models.CharField(max_length=20, default="GSM-7")
    segmentNumber = models.CharField(max_length=255, blank=True, null=True)
    characterCount = models.CharField(max_length=255, blank=True, null=True)
    concatenated_reference = models.SmallIntegerField(null=True, blank=True)  # 0-255
    failure_reason = models.TextField(null=True, blank=True)

    queued_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)

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

    def save(self, *args, **kwargs):
        # 1. Save the SMSMessage to the database first
        super().save(*args, **kwargs)

        # 2. Instantly force the Transaction to match our status!
        if self.status:
            # Import inside the function to prevent circular import crashes
            from squadServices.models.transaction.transaction import (
                ClientTransaction,
                VendorTransaction,
            )

            # Sync Client Transaction
            ClientTransaction.objects.filter(message=self).update(status=self.status)

            # Sync Vendor Transaction
            VendorTransaction.objects.filter(message=self).update(status=self.status)

            print(
                f"🔥 HARDWIRED SUCCESS: Synced Client & Vendor Transactions for Msg #{self.id} to '{self.status}'"
            )

    class Meta:
        ordering = ["-updatedAt"]
        # Force Django to look for the lowercase table in Postgres
        # while keeping the app label as 'squadServices'
        db_table = "squadServices_smsmessage"


class SMSMessagePart(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending"),
        ("QUEUED", "Queued"),
        ("DELIVERED", "Delivered"),
        ("SUBMITTED", "Submitted"),
        ("FAILED", "Failed"),
    )
    text = models.TextField(
        null=True, blank=True, help_text="The decoded text chunk for this segment"
    )
    # Links back to the parent message
    message = models.ForeignKey(
        "SMSMessage", related_name="parts", on_delete=models.CASCADE
    )

    # Tracking the pieces
    part_no = models.IntegerField()
    part_total = models.IntegerField()
    udh_ref = models.IntegerField()
    udh_hex = models.CharField(
        max_length=100, null=True, blank=True
    )  # The raw string like "050003B20201"
    # esm_class = 0x40 tells the vendor "The first 6 bytes are routing instructions!"
    esm_class = models.IntegerField(default=0x00)

    # The actual payload (UDH bytes + Text chunk bytes)
    short_message = models.BinaryField()

    # State tracking
    submit_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="QUEUED"
    )
    vendor_msg_id = models.CharField(max_length=100, null=True, blank=True)

    # 0: ESME_ROK (Success. The vendor accepted the message into their system.)
    # 11: ESME_RINVDSTADR (Immediate failure: The destination phone number is completely invalid or missing digits.)
    # 20: ESME_RMSGQFUL (Immediate failure: The vendor's message queue is full and they cannot accept more messages right now.)
    # 88: ESME_RTHROTTLED (Immediate failure: You are sending messages faster than your allowed TPS / Transactions Per Second. You are being throttled.)
    vendor_submit_status = models.IntegerField(null=True, blank=True)

    submit_attempts = models.IntegerField(default=0)
    failure_reason = models.TextField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_submit_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Msg {self.message.id} - Part {self.part_no}/{self.part_total}"

    class Meta:
        # Ensures you don't accidentally create duplicate segment numbers for the same parent message
        unique_together = ("message", "part_no")
        ordering = ["-created_at"]


class MessageAttempt(models.Model):
    """Tracks every time your server tries to send a segment to the vendor."""

    ATTEMPT_STATUS_CHOICES = (
        ("ATTEMPTING", "Attempting"),
        ("SUBMITTED", "Submitted"),
        ("FAILED", "Failed"),
        ("DELIVERED", "Delivered"),
    )
    message = models.ForeignKey("SMSMessage", on_delete=models.CASCADE)
    segment = models.ForeignKey(
        "SMSMessagePart", on_delete=models.CASCADE, null=True, blank=True
    )
    attempt_number = models.IntegerField()
    provider = models.CharField(
        max_length=50, null=True, blank=True
    )  # e.g., 'RouteMobile'
    provider_message_id = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=ATTEMPT_STATUS_CHOICES)
    request_payload = JSONField(null=True, blank=True)
    response_payload = JSONField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-started_at"]


class DLREvent(models.Model):
    """An append-only log of every receipt the vendor sends back to you."""

    EVENT_TYPE_CHOICES = (
        ("SUBMITTED", "Submitted"),
        ("DELIVERED", "Delivered"),
        ("FAILED", "Failed"),
        ("REJECTED", "Rejected"),
        ("EXPIRED", "Expired"),
        ("UNDELIVERABLE", "Undeliverable"),
    )
    message = models.ForeignKey("SMSMessage", on_delete=models.CASCADE)
    segment = models.ForeignKey(
        "SMSMessagePart", on_delete=models.CASCADE, null=True, blank=True
    )
    provider_message_id = models.CharField(max_length=255, null=True, blank=True)
    event_type = models.CharField(max_length=30, choices=EVENT_TYPE_CHOICES)
    segment_number = models.IntegerField(null=True, blank=True)
    status_code = models.CharField(max_length=20, null=True, blank=True)
    status_description = models.TextField(null=True, blank=True)
    raw_payload = JSONField(null=True, blank=True)
    received_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-received_at"]


class MessageAuditLog(models.Model):
    """Tracks every state change of a message or segment for debugging and billing disputes."""

    AUDIT_STATUS_CHOICES = (
        ("queued", "Queued"),
        ("sent", "Sent"),
        ("delivered", "Delivered"),
        ("failed", "Failed"),
        ("partially_delivered", "Partially Delivered"),
        ("QUEUED", "Part Queued"),
        ("SUBMITTED", "Part Submitted"),
        ("DELIVERED", "Part Delivered"),
        ("FAILED", "Part Failed"),
    )
    # Django handles the ID automatically as a BigAutoField
    message = models.ForeignKey(
        "SMSMessage", on_delete=models.CASCADE, related_name="audit_logs"
    )
    segment = models.ForeignKey(
        "SMSMessagePart",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="audit_logs",
    )

    from_status = models.CharField(
        max_length=20, choices=AUDIT_STATUS_CHOICES, null=True, blank=True
    )
    to_status = models.CharField(max_length=20, choices=AUDIT_STATUS_CHOICES)

    # You can link this to your User model, or keep it as a string (e.g., 'system', 'vendor_dlr', 'admin_sweta')
    changed_by = models.CharField(max_length=100, default="system")

    reason = models.TextField(null=True, blank=True)
    changed_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = "message_audit_log"
        # This replicates the INDEX you were trying to write in SQL!
        indexes = [
            models.Index(fields=["message"]),
            models.Index(fields=["segment"]),
        ]

    def __str__(self):
        return f"Msg {self.message.id}: {self.from_status} -> {self.to_status}"


class MultipartBuffer(models.Model):
    """Temporary waiting room for UDH multipart SMS chunks."""

    system_id = models.CharField(max_length=100)
    destination = models.CharField(max_length=50)
    ref_num = models.IntegerField()  # The UDH Reference Number
    total_parts = models.IntegerField()
    part_num = models.IntegerField()
    text_chunk = models.TextField()  # The decoded text for this specific part
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Prevents duplicate saves if the client has a network hiccup and retries a part
        unique_together = ("system_id", "destination", "ref_num", "part_num")
