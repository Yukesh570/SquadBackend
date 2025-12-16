from django.conf import settings
from django.db import models

from squadServices.models.country import Country, Currency, Entity, State, TimeZone

PERIOD_CHOICES = [
    ("LTD", "Limited"),
    ("UNL", "Unlimited"),
]
EMAIL_CHOICES = [
    ("CMP", "Company"),
    ("SUP", "Support"),
]


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
    companyEmail = models.EmailField(null=True, blank=True)
    supportEmail = models.EmailField(null=True, blank=True)
    billingEmail = models.EmailField(null=True, blank=True)
    ratesEmail = models.EmailField(null=True, blank=True)
    lowBalanceAlertEmail = models.EmailField(null=True, blank=True)
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="companys"
    )
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name="states")
    category = models.ForeignKey(
        CompanyCategory, on_delete=models.CASCADE, related_name="companyCategorys"
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
        Entity, on_delete=models.CASCADE, related_name="entities"
    )

    customerCreditLimit = models.DecimalField(
        max_digits=10, decimal_places=4, default=0.00
    )
    vendorCreditLimit = models.DecimalField(
        max_digits=10, decimal_places=4, default=0.00
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
