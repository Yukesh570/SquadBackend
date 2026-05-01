from django.conf import settings
from django.db import models

from squadServices.models.country import Country


class Operators(models.Model):
    name = models.TextField()
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="countryOperators",
        null=True,
        blank=True,
    )
    # remove mnc
    # MNC = models.IntegerField(null=True, blank=True)
    operatorCode = models.CharField(max_length=20, null=True, blank=True)
    status = models.CharField(
        max_length=10,
        choices=[("ACTIVE", "Active"), ("INACTIVE", "Inactive")],
        default="ACTIVE",
    )
    notes = models.TextField(null=True, blank=True)
    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="operator_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="operator_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        short_name = (self.name[:40] + "...") if len(self.name) > 40 else self.name
        return f"{self.id} - {short_name}"


class OperatorNetworkCode(models.Model):
    NETWORK_TYPES = [
        ("GSM", "GSM"),
        ("LTE", "LTE"),
        ("5G", "5G"),
        ("CDMA", "CDMA"),
        ("UNKNOWN", "Unknown"),
    ]

    operator = models.ForeignKey(
        Operators, on_delete=models.CASCADE, related_name="network_codes"
    )
    country = models.ForeignKey(Country, on_delete=models.CASCADE)
    MCC = models.CharField(max_length=3, help_text="Mobile Country Code")
    MNC = models.CharField(max_length=3, help_text="Mobile Network Code")

    # ⚡️ NEW: To match the 'mcc_mnc' STORED GENERATED column in SQL
    # We use a property for logic, but for high-speed routing, we add a DB index
    @property
    def mcc_mnc(self):
        return f"{self.MCC}{self.MNC}"

    networkType = models.CharField(
        max_length=10, choices=NETWORK_TYPES, default="UNKNOWN"
    )
    isPrimary = models.BooleanField(default=False)
    status = models.CharField(
        max_length=10,
        choices=[("ACTIVE", "Active"), ("INACTIVE", "Inactive")],
        default="ACTIVE",
    )

    effectiveFrom = models.DateField(null=True, blank=True)
    effectiveTo = models.DateField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="operatorNetworkCode_updated_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="operatorNetworkCode_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]
        db_table = "squadServices_operatornetworkcode"
        unique_together = ("operator", "MCC", "MNC")
        indexes = [
            models.Index(fields=["MCC", "MNC"]),
            models.Index(fields=["country", "MCC", "MNC"]),
        ]

    def __str__(self):
        return f"{self.operator} ({self.MCC}{self.MNC})"
