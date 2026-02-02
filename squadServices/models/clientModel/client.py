from django.conf import settings
from django.db import models

from squadServices.models.company import Company


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
    status = models.CharField(
        max_length=11,
        choices=STATUS_CHOICES,
        default="ACTIVE",
    )
    route = models.CharField(
        max_length=20,
        choices=ROUTE_CHOICES,
        default="DIRECT",
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
    allowNetting = models.BooleanField(default=False)
    ipWhitelist = models.JSONField(default=list, blank=True)
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
