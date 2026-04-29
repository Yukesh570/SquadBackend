from django.db import models
from django.conf import settings


class GeneralSetting(models.Model):
    # Setup dropdown choices for the admin panel
    LANGUAGE_CHOICES = (
        ("en", "English"),
        ("es", "Spanish"),
        ("fr", "French"),
        # Add more languages as needed
    )

    CURRENCY_CHOICES = (
        ("EUR", "Euro (EUR)"),
        ("USD", "US Dollar (USD)"),
        ("GBP", "British Pound (GBP)"),
        ("NPR", "Nepalese Rupee (NPR)"),
    )

    companyName = models.CharField(max_length=255, default="Squad Telekom LLC")
    defaultLanguage = models.CharField(
        max_length=10, choices=LANGUAGE_CHOICES, default="en"
    )
    defaultTimezone = models.CharField(
        max_length=50,
        default="UTC",
        help_text="Standard timezone string (e.g., UTC, Europe/London)",
    )
    dateFormat = models.CharField(max_length=20, default="YYYY-MM-DD")
    datetimeFormat = models.CharField(max_length=50, default="YYYY-MM-DD HH:MM:SS")
    baseCurrency = models.CharField(
        max_length=10, choices=CURRENCY_CHOICES, default="EUR"
    )
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="generalSetting_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "General Setting"
        verbose_name_plural = "General Settings"

    def __str__(self):
        return f"System Settings: {self.companyName}"

    def save(self, *args, **kwargs):
        """
        ⚡️ THE SINGLETON TRICK:
        This prevents anyone from creating a second row of settings.
        If a row already exists, it will strictly overwrite the first row.
        """
        if not self.pk and GeneralSetting.objects.exists():
            self.pk = GeneralSetting.objects.first().pk
        super().save(*args, **kwargs)
