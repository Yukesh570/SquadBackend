from django.conf import settings
from django.db import models


class MappingSetup(models.Model):
    ratePlan = models.CharField(max_length=255, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    countryCode = models.CharField(max_length=255, null=True, blank=True)
    timeZone = models.CharField(max_length=255, null=True, blank=True)

    network = models.CharField(max_length=255, null=True, blank=True)
    MCC = models.CharField(max_length=255, null=True, blank=True)
    MNC = models.CharField(max_length=255, null=True, blank=True)
    rate = models.CharField(max_length=255, null=True, blank=True)
    dateTime = models.CharField(max_length=255, null=True, blank=True)

    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="mappingSetup_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="mappingSetup_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        return self.ratePlan
