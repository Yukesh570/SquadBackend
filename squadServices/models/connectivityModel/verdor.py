from django.conf import settings
from django.db import models
import uuid

from squadServices.models.company import Company
from squadServices.models.connectivityModel.smpp import SMPP
from django.utils import timezone

CONNECTION_TYPE_CHOICES = [
    ("SMPP", "SMPP"),
    ("HTTP", "HTTP"),
]

POLICY_CHOICES = [
    ("ON ATTEMPT", "on attempt"),
    ("ON SUBMIT", "on submit"),
    ("ON DELIVERED", "on delivered"),
]


class Vendor(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="vendor"
    )
    smpp = models.ForeignKey(
        SMPP, on_delete=models.DO_NOTHING, related_name="smpp", null=True, blank=True
    )
    ratePlanName = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Type the exact name of the ratePlan used in the VendorRate table",
    )
    bindStatus = models.CharField(
        max_length=10,
        choices=[("ONLINE", "Online"), ("OFFLINE", "Offline")],
        default="OFFLINE",
        help_text="Live indicator of whether the vendor is currently connected to our SMPP server.",
    )

    profileName = models.CharField(max_length=255)
    connectionType = models.CharField(
        max_length=4,
        choices=CONNECTION_TYPE_CHOICES,
        default="SMPP",
        verbose_name="connection type",
    )
    invoicePolicy = models.CharField(
        max_length=20,
        choices=POLICY_CHOICES,
        default="ON ATTEMPT",
    )
    lastAttemptAt = models.DateTimeField(null=True, blank=True)
    lastRetryAt = models.DateTimeField(null=True, blank=True)
    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vendor_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vendor_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        return self.profileName


class SMPPLogLevel(models.TextChoices):
    DEBUG = "DEBUG", "Debug"
    INFO = "INFO", "Info"
    WARNING = "WARNING", "Warning"
    ERROR = "ERROR", "Error"


class VendorPolicy(models.Model):

    vendor = models.OneToOneField(
        Vendor, on_delete=models.CASCADE, related_name="policy"
    )
    sourceAddrTon = models.IntegerField(default=5, help_text="Source Addr Ton")
    sourceAddrNpi = models.IntegerField(default=0, help_text="Source Addr NPI")
    destAddrTon = models.IntegerField(default=1, help_text="Destination Addr Ton")
    destAddrNpi = models.IntegerField(default=1, help_text="Destination Addr NPI")
    addrTon = models.IntegerField(default=1, null=True, blank=True)
    addrNpi = models.IntegerField(default=1, null=True, blank=True)

    # --- 2. SPEED & QUEUEING ---
    rateTps = models.IntegerField(
        default=50, help_text="Rate/TPS (Max messages per second)"
    )
    sendQueueLimit = models.IntegerField(
        default=10, help_text="Send Queue Limit (Window Size)"
    )
    delayTime = models.FloatField(default=10.0, help_text="Delay Time (Seconds)")

    maxSession = models.IntegerField(
        default=2, help_text="Max concurrent SMPP sessions for this client"
    )

    # --- 3. TIMEOUTS & HEARTBEATS ---
    responseTimeout = models.FloatField(
        default=30.0, help_text="Response Timeout (Seconds)"
    )
    enquireLinkInterval = models.FloatField(
        default=30.0, help_text="Enquire Link (Seconds)"
    )
    connectionTimeout = models.FloatField(
        default=10.0, help_text="Connection Timeout (Seconds)"
    )

    # --- 4. RETRIES & RECOVERY ---
    connectionRetryDelay = models.FloatField(
        default=5.0, help_text="Connection Retry Delay (Seconds)"
    )
    connectionRetryCount = models.IntegerField(
        default=3, help_text="Connection Retry Count"
    )
    bindRetryDelay = models.FloatField(
        default=5.0, help_text="Bind Retry Delay (Seconds)"
    )
    bindRetryCount = models.IntegerField(default=3, help_text="Bind Retry Count")
    connectionRecoveryDelay = models.FloatField(
        default=60.0, help_text="Connection Recovery Delay (Seconds)"
    )

    # --- 5. LOGGING & TLVs ---
    logLevel = models.CharField(
        max_length=10,
        choices=SMPPLogLevel.choices,
        default=SMPPLogLevel.INFO,
        help_text="Log Level",
    )
    tlvTag = models.CharField(
        max_length=50, null=True, blank=True, help_text="TLV Tag (e.g. 0x1401)"
    )
    tlvValue = models.CharField(
        max_length=255, null=True, blank=True, help_text="TLV Value"
    )
    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vendorPolicy_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vendorPolicy_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)


class VendorSession(models.Model):
    sessionId = models.CharField(max_length=64, primary_key=True, default=uuid.uuid4)
    # Links to the Vendor (The business entity/config)
    vendor = models.ForeignKey(
        "Vendor", on_delete=models.CASCADE, related_name="sessions"
    )
    # The IP you connected TO
    gatewayIp = models.CharField(max_length=45)

    bindType = models.CharField(max_length=20)  # e.g. TRANSCEIVER

    connectedAt = models.DateTimeField(default=timezone.now)
    disconnectedAt = models.DateTimeField(null=True, blank=True)

    # ONLINE, OFFLINE, FAILED
    status = models.CharField(max_length=20, default="ONLINE")

    # Store the reason for disconnection (e.g., "Connection reset by peer")
    error_reason = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "vendorSessions"
        ordering = ["-connectedAt"]

    def __str__(self):
        return f"Session {self.sessionId} - {self.vendor.profileName}"
