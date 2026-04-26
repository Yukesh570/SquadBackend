from django.conf import settings
from django.db import models

from squadServices.models.country import Country, Currency, Entity, State, TimeZone
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

PERIOD_CHOICES = [
    ("LTD", "Limited"),
    ("UNL", "Unlimited"),
]
EMAIL_CHOICES = [
    ("CMP", "Company"),
    ("SUP", "Support"),
]


def validate_comma_separated_emails(value):
    """Validates that a string of comma-separated emails are all valid."""
    if not value:
        return

    # Split by comma and strip whitespace
    emails = [email.strip() for email in value.split(",")]

    for email in emails:
        if email:  # Ignore empty strings (e.g., if someone types "a@a.com, ")
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError(f"'{email}' is not a valid email address.")
        else:
            raise ValidationError("Found an empty email address in the list.")


class CompanyCategory(models.Model):
    name = models.CharField(max_length=100)
    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="category_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="category_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        return self.name


class CompanyStatus(models.Model):
    name = models.CharField(max_length=100)
    isDeleted = models.BooleanField(default=False)

    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="status_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="status_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        return self.name


class Company(models.Model):
    name = models.CharField(max_length=100)
    shortName = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, null=True, blank=True)
    companyEmail = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        validators=[validate_comma_separated_emails],
        help_text="Separate multiple emails with a comma.",
    )
    supportEmail = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        validators=[validate_comma_separated_emails],
    )
    billingEmail = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        validators=[validate_comma_separated_emails],
    )
    ratesEmail = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        validators=[validate_comma_separated_emails],
    )
    lowBalanceAlertEmail = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        validators=[validate_comma_separated_emails],
    )
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="companys"
    )
    state = models.ForeignKey(
        State, on_delete=models.CASCADE, related_name="states", null=True, blank=True
    )
    category = models.ForeignKey(
        CompanyCategory,
        on_delete=models.CASCADE,
        related_name="companyCategorys",
        null=True,
        blank=True,
    )
    status = models.ForeignKey(
        CompanyStatus, on_delete=models.CASCADE, related_name="companyStatuss"
    )
    currency = models.ForeignKey(
        Currency, on_delete=models.CASCADE, related_name="companyCurrencies"
    )
    timeZone = models.ForeignKey(
        TimeZone, on_delete=models.CASCADE, related_name="companyTimeZones"
    )
    businessEntity = models.ForeignKey(
        Entity, on_delete=models.CASCADE, related_name="entities", null=True, blank=True
    )

    customerCreditLimit = models.DecimalField(
        max_digits=10, decimal_places=4, default=0.00
    )
    vendorCreditLimit = models.DecimalField(
        max_digits=10, decimal_places=4, default=0.00
    )

    usedCustomerCredit = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        default=0.00,
        help_text="Tracks total amount this company owes you (Customer spend)",
    )
    usedVendorCredit = models.DecimalField(
        max_digits=18,
        decimal_places=4,
        default=0.00,
        help_text="Tracks total amount you owe this company (Vendor spend)",
    )

    balanceAlertAmount = models.DecimalField(
        max_digits=10, decimal_places=4, default=0.00
    )
    referencNumber = models.CharField(max_length=100, null=True, blank=True)
    vatNumber = models.CharField(max_length=50, null=True, blank=True)
    address = models.CharField(max_length=100)
    validityPeriod = models.CharField(
        max_length=3,
        choices=PERIOD_CHOICES,
        default="UNL",
        verbose_name="Validity Period",
    )
    defaultEmail = models.CharField(
        max_length=3, choices=EMAIL_CHOICES, default="CMP", verbose_name="Email Period"
    )
    onlinePayment = models.BooleanField(default=True, verbose_name="Online Payment")

    companyBlocked = models.BooleanField(default=False, verbose_name="Company Blocked")

    allowWhiteListedCards = models.BooleanField(
        default=False, verbose_name="Allow White Listed Cards"
    )

    sendDailyReports = models.BooleanField(
        default=True, verbose_name="Send Daily Reports"
    )

    allowNetting = models.BooleanField(default=False, verbose_name="Allow Netting")

    showHlrApi = models.BooleanField(default=False, verbose_name="Show HLR API")

    enableVendorPanel = models.BooleanField(
        default=False, verbose_name="Enable Vendor Panel"
    )

    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="companies_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="companies_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        return self.name
