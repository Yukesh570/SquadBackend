from django.db import models

from squad import settings
from squadServices.models.clientModel.client import Client
from squadServices.models.connectivityModel.verdor import Vendor
from squadServices.models.smpp.smppSMS import SMSMessage


class TransactionType(models.TextChoices):
    DEDUCTION = "DEDUCTION", "Deduction"
    REFUND = "REFUND", "Refund"
    TOPUP = "TOPUP", "Top-Up"


class ClientTransaction(models.Model):
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, related_name="transactions"
    )
    message = models.ForeignKey(
        SMSMessage, on_delete=models.SET_NULL, null=True, blank=True
    )

    transactionType = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        default=TransactionType.DEDUCTION,
    )

    # --- NEW BILLING CONTEXT FIELDS ---
    segments = models.IntegerField(
        null=True, blank=True, help_text="Number of SMS parts billed"
    )
    ratePerSegment = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    # ----------------------------------

    amount = models.DecimalField(max_digits=10, decimal_places=4)  # Segments * Rate
    balanceSpent = models.DecimalField(max_digits=10, decimal_places=4)
    description = models.CharField(max_length=255, blank=True)

    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="clientTransactionCreated",
    )
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="clientTransactionUpdated",
    )
    isDeleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.client.name} | {self.transactionType} | Segs: {self.segments} | Amt: {self.amount}"


class VendorTransaction(models.Model):
    vendor = models.ForeignKey(
        Vendor, on_delete=models.CASCADE, related_name="transactions"
    )
    message = models.ForeignKey(
        SMSMessage, on_delete=models.SET_NULL, null=True, blank=True
    )

    transactionType = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
        default=TransactionType.DEDUCTION,
    )

    # --- NEW BILLING CONTEXT FIELDS ---
    segments = models.IntegerField(null=True, blank=True)
    ratePerSegment = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True
    )
    # ----------------------------------

    amount = models.DecimalField(max_digits=10, decimal_places=4)
    balanceSpent = models.DecimalField(max_digits=10, decimal_places=4)
    description = models.CharField(max_length=255, blank=True)

    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vendorTransactionCreated",
    )
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vendorTransactionUpdated",
    )
    isDeleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.vendor.profileName} | {self.transactionType} | Segs: {self.segments} | Amt: {self.amount}"
