from django.conf import settings
from django.db import models

from squadServices.models.country import Country, TimeZone

CURRENCY_CODE_CHOICES = [
    ("AUD", "AUD"),
    ("NPR", "NPR"),
    ("INR", "INR"),
    ("ARD", "ARD"),
    ("EUR", "EUR"),
]


class VendorRate(models.Model):

    ratePlan = models.CharField(max_length=255)
    currencyCode = models.CharField(max_length=255, null=True, blank=True)
    network = models.CharField(max_length=255, null=True, blank=True)

    countryCode = models.IntegerField(null=True, blank=True)
    timeZone = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    MCC = models.IntegerField(null=True, blank=True)
    MNC = models.IntegerField(null=True, blank=True)

    rate = models.FloatField(null=True, blank=True)
    remark = models.CharField(max_length=255, null=True, blank=True)
    dateTime = models.DateTimeField(null=True, blank=True)

    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vendorRate_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vendorRate_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        return self.ratePlan
