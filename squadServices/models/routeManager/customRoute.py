from django.db import models

from squad import settings
from squadServices.models.clientModel.client import Client
from squadServices.models.company import Company
from squadServices.models.connectivityModel.verdor import Vendor
from squadServices.models.country import Country
from squadServices.models.operators.operators import Operators

STATUS_CHOICES = [
    ("ACTIVE", "Active"),
    ("INACTIVE", "Inactive"),
]


class CustomRoute(models.Model):
    name = models.CharField(max_length=100)
    orginatingCompany = models.ForeignKey(
        Company,
        on_delete=models.DO_NOTHING,
        related_name="orginatingCompanyCustomRoutes",
    )
    orginatingClient = models.ForeignKey(
        Client,
        on_delete=models.DO_NOTHING,
        related_name="orginatingClientCustomRoutes",
    )
    priority = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="INACTIVE")
    country = models.ForeignKey(
        Country,
        on_delete=models.DO_NOTHING,
        related_name="countryCustomRoutes",
    )

    operator = models.ForeignKey(
        Operators, on_delete=models.DO_NOTHING, related_name="operatorCustomRoutes"
    )

    terminatingCompany = models.ForeignKey(
        Company,
        on_delete=models.DO_NOTHING,
        related_name="terminatingCompanyCustomRoutes",
    )
    terminatingVendor = models.ForeignKey(
        Vendor,
        on_delete=models.DO_NOTHING,
        related_name="terminatingVendorCustomRoutes",
    )
    isDeleted = models.BooleanField(default=False)

    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="customRoute_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="customRoute_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        return self.name
