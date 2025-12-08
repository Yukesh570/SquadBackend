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


class CustomerRate(models.Model):

    ratePlan = models.CharField(max_length=255)
    currencyCode = models.CharField(
        max_length=4,
        choices=CURRENCY_CODE_CHOICES,
        default="NPR",
        verbose_name="currency code",
    )
    countryCode = models.IntegerField(null=True, blank=True)

    timeZone = models.ForeignKey(
        TimeZone, on_delete=models.CASCADE, related_name="timeZoneCustomer"
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="countryCustomer",
        null=True,
        blank=True,
    )
    MCC = models.IntegerField(null=True, blank=True)
    MNC = models.IntegerField(null=True, blank=True)

    rate = models.IntegerField(null=True, blank=True)
    remark = models.CharField(max_length=255, null=True, blank=True)
    dateTime = models.DateTimeField(null=True, blank=True)

    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="customerRate_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="customerRate_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.ratePlan
