from django.db import models
from django.conf import settings


class ClientInvoice(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),  # For when they click "Preview"
        ("GENERATED", "Generated"),  # For when they click "Generate"
        ("SENT", "Sent"),
        ("PAID", "Paid"),
    ]

    client = models.ForeignKey(
        "Client", on_delete=models.CASCADE, related_name="clientInvoices"
    )

    # The dates used to generate this specific invoice
    billingPeriodStart = models.DateField()  # Matches From Date
    billingPeriodEnd = models.DateField()  # Matches To Date
    invoiceDate = models.DateField()

    # The actual calculated data
    invoiceNumber = models.CharField(max_length=50, unique=True)
    totalAmount = models.DecimalField(max_digits=12, decimal_places=4, default=0.00)
    totalSegments = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")

    # Where you will store the generated PDF report
    invoicePdf = models.FileField(
        upload_to="invoices/clients/%Y/%m/", null=True, blank=True
    )
    accountManager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_invoices",
        help_text="The internal user managing this client/invoice.",
    )

    # --- Standard Audit Fields ---
    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="invoice_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-createdAt"]
        db_table = "squadServices_clientinvoice"

    def __str__(self):
        return f"Invoice {self.invoiceNumber} - {self.client.name}"


class VendorInvoice(models.Model):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),  # For when they click "Preview"
        ("GENERATED", "Generated"),  # For when they click "Generate"
        ("SENT", "Sent"),
        ("PAID", "Paid"),
    ]

    vendor = models.ForeignKey(
        "Vendor", on_delete=models.CASCADE, related_name="vendorInvoices"
    )

    # The dates used to generate this specific invoice
    billingPeriodStart = models.DateField()  # Matches From Date
    billingPeriodEnd = models.DateField()  # Matches To Date
    invoiceDate = models.DateField()

    # The actual calculated data
    invoiceNumber = models.CharField(max_length=50, unique=True)
    totalAmount = models.DecimalField(max_digits=12, decimal_places=4, default=0.00)
    totalSegments = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="DRAFT")

    # Where you will store the generated PDF report
    invoicePdf = models.FileField(
        upload_to="invoices/clients/%Y/%m/", null=True, blank=True
    )
    accountManager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_vendorInvoices",
        help_text="The internal user managing this vendor/invoice.",
    )

    # --- Standard Audit Fields ---
    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vendorInvoice_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-createdAt"]
        db_table = "squadServices_vendorinvoice"

    def __str__(self):
        return f"Invoice {self.invoiceNumber} - {self.vendor.profileName}"
