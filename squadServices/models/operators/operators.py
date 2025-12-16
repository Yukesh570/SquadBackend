from django.conf import settings
from django.db import models

from squadServices.models.country import Country


class Operators(models.Model):
    name = models.TextField()
    country = models.ForeignKey(
        Country,
        on_delete=models.DO_NOTHING,
        related_name="countryOperators",
        null=True,
        blank=True,
    )
    MNC = models.IntegerField(null=True, blank=True)

    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="operator_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="operator_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        short_name = (self.name[:40] + "...") if len(self.name) > 40 else self.name
        return f"{self.id} - {short_name}"
