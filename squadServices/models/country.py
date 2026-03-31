from django.conf import settings
from django.db import models


class Country(models.Model):
    name = models.CharField(max_length=100)
    countryCode = models.CharField(max_length=100)
    MCC = models.CharField(max_length=100)
    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="countries_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="countries_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class State(models.Model):
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="states"
    )
    name = models.CharField(max_length=100)  # User-friendly name
    isDeleted = models.BooleanField(default=False)

    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="states_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="states_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        return self.name


class Currency(models.Model):
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="currencies"
    )
    name = models.CharField(max_length=100)
    isDeleted = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="currency_created",
    )
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="currency_updated",
    )

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        return self.name


class Entity(models.Model):
    # --- Dropdown Choices ---
    WEEK_DAYS = [
        ("SUNDAY", "Sunday"),
        ("MONDAY", "Monday"),
    ]

    # --- Core Business Information ---
    legalEntityName = models.CharField(max_length=255)
    companyName = models.CharField(max_length=255)

    # Assuming this tracks the current or starting invoice number for the company
    invoiceNumber = models.IntegerField(default=1)  # sequence tracker or a counter
    weekCommencing = models.CharField(
        max_length=10, choices=WEEK_DAYS, default="MONDAY"
    )

    vatRegistrationNumber = models.CharField(max_length=50, blank=True, null=True)

    # --- Contact & Location ---
    phone = models.CharField(max_length=20, blank=True, null=True)
    emailAddress = models.EmailField(
        blank=True, null=True
    )  # Validates proper email format
    businessAddress = models.TextField(
        blank=True, null=True
    )  # TextField allows multi-line addresses

    # --- Financial & Branding ---
    bankAccountDetail = models.TextField(
        blank=True,
        null=True,
        help_text="Store Bank Name, Account Number, and Routing/Swift codes here.",
    )
    companyLogo = models.ImageField(upload_to="entities/logos/", blank=True, null=True)

    # --- Standard Audit Fields (From your original code) ---
    isDeleted = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="entities_created",
    )
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="entities_updated",
    )

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        return self.companyName


class TimeZone(models.Model):
    name = models.CharField(max_length=100)
    isDeleted = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="timeZone_created",
    )
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="timeZone_updated",
    )

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        return self.name
