from django.conf import settings
from django.db import models

from squadServices.models.company import Company
from django.utils import timezone
import uuid

STATUS_CHOICES = [
    ("ACTIVE", "active"),
    ("TRIAL", "trial"),
    ("SUSPENDED", "suspended"),
]

ROUTE_CHOICES = [
    ("DIRECT", "direct"),
    ("HIGH QUALITY", "high quality"),
    ("SIM", "SIM"),
    ("WHOLESALE", "wholesale"),
    ("FULL", "full"),
]
POLICY_CHOICES = [
    ("ON ATTEMPT", "on attempt"),
    ("ON SUBMIT", "on submit"),
    ("ON DELIVERED", "on delivered"),
]
PAYMENTTERMS_CHOICES = [
    ("PREPAID", "prepaid"),
    ("POSTPAID", "postpaid"),
    ("NET7", "Net7"),
    ("NET15", "Net15"),
    ("NET30", "Net30"),
]


class Client(models.Model):

    name = models.CharField(max_length=255)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="clientCompany"
    )
    ratePlanName = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Type the exact name of the ratePlan used in the customerRate table",
    )
    status = models.CharField(
        max_length=11,
        choices=STATUS_CHOICES,
        default="ACTIVE",
    )
    # Add this below your other status fields in the Client model
    bindStatus = models.CharField(
        max_length=10,
        choices=[("ONLINE", "Online"), ("OFFLINE", "Offline")],
        default="OFFLINE",
        help_text="Live indicator of whether the client is currently connected to our SMPP server.",
    )
    route = models.CharField(
        max_length=20,
        choices=ROUTE_CHOICES,
        default="DIRECT",
    )
    enableDlr = models.BooleanField(
        default=True,
        help_text="Enable to allow this client to receive final Delivery Receipts. Disable to save server resources.",
    )
    paymentTerms = models.CharField(
        max_length=8,
        choices=PAYMENTTERMS_CHOICES,
        default="PREPAID",
    )
    creditLimit = models.DecimalField(max_digits=18, decimal_places=4, default=0.00)
    balanceAlertAmount = models.DecimalField(
        max_digits=18, decimal_places=4, default=0.00
    )

    invoicePolicy = models.CharField(
        max_length=20,
        choices=POLICY_CHOICES,
        default="ON ATTEMPT",
    )

    # for now......
    usedCredit = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        default=0.00,
        help_text="Tracks how much this specific SMPP account has spent",
    )
    allowNetting = models.BooleanField(default=False)
    smppUsername = models.CharField(max_length=255)
    smppPassword = models.CharField(max_length=255)
    internalNotes = models.TextField(null=True, blank=True)

    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="client_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="client_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]
        db_table = "squadServices_client"  # Add this line

    def __str__(self):
        return self.name


class ClientPolicy(models.Model):

    client = models.OneToOneField(
        Client, on_delete=models.CASCADE, related_name="clientPolicy"
    )
    # Speed & Throughput Control
    maxTps = models.IntegerField(
        default=50, help_text="Max SUBMIT_SM per second (0=unlimited)"
    )
    maxQueueDepth = models.IntegerField(
        default=1000,
        help_text="Max number of messages to queue for this client when rate limits are exceeded",
    )

    # The "Window" (Congestion Control)
    # This is how many messages a client can send without waiting for an answer.
    maxWindowPerSession = models.IntegerField(
        default=10, help_text="Max outstanding unacked SUBMIT_SM"
    )
    # If a client has multiple connections open at once, this is the limit across all of them combined.
    maxWindowGlobal = models.IntegerField(
        default=100, help_text="Max outstanding unacked SUBMIT_SM across all sessions"
    )

    # Session & Timeout Management

    # Limits how many simultaneous logins a client can have.
    # This prevents a client from opening 100 connections to try and bypass your TPS limits.
    maxSessions = models.IntegerField(
        default=2, help_text="Max concurrent SMPP sessions for this client"
    )

    # If a client logs in but doesn't send anything for 60 seconds,
    # your server will automatically kick them off to save resources.
    idleTimeoutSec = models.IntegerField(
        default=60,
        help_text="Time in seconds before SMPP connection times out due to inactivity",
    )

    #: If you send a message to a vendor on behalf of the client and
    # the vendor doesn't answer within 30 seconds, your server tells the client the request timed out.
    submitTimeoutSec = models.IntegerField(
        default=30,
        help_text="Time in seconds before a SUBMIT_SM is considered timed out if no response is received",
    )

    # Security & Compliance
    # If set to approvedOnly, the client can only send messages using a "Sender ID" (like "SQUAD")
    # that you have pre-approved in the database.
    senderIdPolicy = models.CharField(max_length=20, default="approvedOnly")
    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="clientPolicy_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="clientPolicy_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]
        db_table = "squadServices_ClientPolicy"  # Add this line

    def __str__(self):
        return f"Policy for {self.client.name}"


class IpWhitelist(models.Model):
    # protocol="both" allows both IPv4 and IPv6
    ip = models.GenericIPAddressField(protocol="both", unpack_ipv4=True)
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="ipWhitelist"
    )
    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="clientIpWhiteList_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True, null=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="clientIpWhiteList_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        db_table = "squadServices_ipwhitelist"

    def __str__(self):
        return f"{self.client.name} - {self.ip}"


class PuskarClient(models.Model):

    name = models.CharField(max_length=255)

    DsmppUsername = models.CharField(max_length=255)
    FsmppUsername = models.CharField(max_length=255)
    smppPassword = models.CharField(max_length=255)

    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="puskarclient_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="puskarclient_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]
        db_table = "squadServices_puskar_client"  # Add this line

    def __str__(self):
        return self.name


class ClientSession(models.Model):
    # Generates a unique 64-char ID automatically if none is provided
    sessionId = models.CharField(max_length=64, primary_key=True, default=uuid.uuid4)
    # Links directly to your existing Client model
    client = models.ForeignKey(
        "Client", on_delete=models.CASCADE, related_name="active_sessions"
    )
    systemId = models.CharField(max_length=50)

    # E.g., 'TRANSMITTER', 'RECEIVER', 'TRANSCEIVER'
    bindType = models.CharField(max_length=20)

    remoteIp = models.CharField(max_length=45)
    remotePort = models.IntegerField()

    connectedAt = models.DateTimeField(default=timezone.now)
    boundAt = models.DateTimeField(default=timezone.now)
    last_activityAt = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, default="ONLINE")

    class Meta:
        db_table = "clientSessions"

    def __str__(self):
        return f"{self.systemId} ({self.remoteIp}:{self.remotePort})"
