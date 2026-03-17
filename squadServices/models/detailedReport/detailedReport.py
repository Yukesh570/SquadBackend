from decimal import Decimal
from django.db import models


class DetailedSMSReport(models.Model):
    STATUS_CHOICES = (
        ("QUEUED", "Queued"),
        ("DELIVERED", "Delivered"),
        ("SUBMITTED", "Submitted"),
        ("FAILED", "Failed"),
    )
    # Link back to the original message just in case
    message = models.OneToOneField(
        "SMSMessage", on_delete=models.CASCADE, related_name="report_row"
    )
    senderId = models.CharField(max_length=50, null=True, blank=True)
    text_message_id = models.CharField(max_length=255, db_index=True)
    vendor_msg_id = models.CharField(max_length=255, db_index=True)

    text = models.TextField(null=True, blank=True)

    part_total = models.IntegerField()
    # --- 1. Origination (Client Side) ---
    clientRate = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal("0.000000"),
        help_text="Price per segment for client",
    )
    client = models.CharField(max_length=255, null=True, blank=True)
    client_charge = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal("0.000000"),
        help_text="The actual cost of this message",
    )

    # --- 2. Routing Details ---
    countryMCC = models.CharField(max_length=100, null=True, blank=True)
    operatorMNC = models.CharField(max_length=100, default="All")
    destination = models.CharField(max_length=50, db_index=True)

    # --- 3. Termination (Vendor Side) ---
    vendor = models.CharField(max_length=255, null=True, blank=True)
    vendorRate = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal("0.000000"),
        help_text="Price per segment from vendor",
    )
    vendor_charge = models.DecimalField(
        max_digits=12,
        decimal_places=6,
        default=Decimal("0.000000"),
        help_text="What the vendor charged you",
    )

    submitStatus = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="QUEUED"
    )

    # --- 5. Timestamps ---
    request_time = models.DateTimeField(null=True, blank=True)
    delivery_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "squadServices_detailed_report"
        ordering = ["-request_time"]

    def __str__(self):
        return f"Report Row: {self.text_message_id} - {self.destination}"
