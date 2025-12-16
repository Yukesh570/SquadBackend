from django.conf import settings
from django.db import models

from squadServices.models.country import Country


class Network(models.Model):
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="networks"
    )
    name = models.CharField(max_length=100)
    MNC = models.IntegerField(null=True, blank=True)

    isDeleted = models.BooleanField(default=False)

    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="network_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="network_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        return self.name
