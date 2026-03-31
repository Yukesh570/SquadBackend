from django.db import models
from django.conf import settings

from squadServices.models.company import Company
from squadServices.models.country import Entity

# Assuming you have these models already, adjust imports as needed
# from squadServices.models.businessEntity import BusinessEntity
# from squadServices.models.tax import Tax


class InvoiceSetup(models.Model):
    FREQUENCY_CHOICES = [
        ("WEEKLY", "Weekly"),
        ("BI_WEEKLY", "Bi-weekly"),
        ("MONTHLY", "Monthly"),
        ("QUARTERLY", "3 Months"),
    ]

    # B. Select company
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="companyInvoiceSetups"
    )

    # C. Display Address of Company
    # (Best Practice: Store an optional override, otherwise fetch dynamically via a property)
    billingAddressOverride = models.TextField(
        null=True,
        blank=True,
        help_text="Leave blank to use the default Company address",
    )

    # D. Select Business Entity
    businessEntity = models.ForeignKey(
        Entity,  # Replace with actual model if imported
        on_delete=models.CASCADE,
        related_name="entityInvoiceSetups",
    )
    # businessEntity = models.ForeignKey(
    #     BusinessEntity, # Replace with actual model if imported
    #     on_delete=models.CASCADE,
    #     related_name="entityInvoiceSetups"
    # )

    # E. Invoice Frequency Selection
    invoiceFrequency = models.CharField(
        max_length=20, choices=FREQUENCY_CHOICES, default="MONTHLY"
    )

    # F. Invoice Due days (Number value)
    dueDays = models.PositiveIntegerField(
        default=0, help_text="Number of days until the invoice is due (e.g., 15, 30)"
    )

    # H. Tax Applied Yes/No Radio Button
    isTaxApplied = models.BooleanField(default=False)

    # G. Tax Selection
    # Assuming you have a Tax model. If it's just a text dropdown, change this to a CharField.
    tax = models.CharField(
        max_length=100,
    )
    # tax = models.ForeignKey(
    #     "Tax",
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     related_name="taxInvoiceSetups",
    # )

    # --- Standard Audit Fields matching your style ---
    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="invoiceSetup_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="invoiceSetup_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]
        db_table = "squadServices_invoicesetup"

    def __str__(self):
        return f"Invoice Setup - {self.company.name}"

    # Helper property for C: Display Address of Company
    @property
    def display_address(self):
        """Returns the override address if provided, otherwise falls back to the Company address."""
        if self.billingAddressOverride:
            return self.billingAddressOverride
        return (
            self.company.address
        )  # Assuming your Company model has an 'address' field
