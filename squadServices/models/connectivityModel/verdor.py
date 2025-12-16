from django.conf import settings
from django.db import models

from squadServices.models.company import Company
from squadServices.models.connectivityModel.smpp import SMPP
from squadServices.models.country import Country, Currency, Entity, State, TimeZone

CONNECTION_TYPE_CHOICES = [
    ("SMPP", "SMPP"),
    ("HTTP", "HTTP"),
]


class Vendor(models.Model):
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="company"
    )
    smpp = models.ForeignKey(
        SMPP, on_delete=models.DO_NOTHING, related_name="smpp", null=True, blank=True
    )
    profileName = models.CharField(max_length=255)
    connectionType = models.CharField(
        max_length=4,
        choices=CONNECTION_TYPE_CHOICES,
        default="SMPP",
        verbose_name="connection type",
    )
    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vendor_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="vendor_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        return self.profileName
