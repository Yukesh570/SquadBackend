from django.conf import settings
from django.db import models


BIND_MODE_CHOICES = [
    ("TRANSMITTER", "transmitter"),
    ("RECEIVER", "receiver"),
    ("TRANSCEIVER", "transceiver"),
]


class Connectivity(models.Model):
    smppHost = models.CharField(max_length=255)
    smppPort = models.IntegerField(default=587)
    systemID = models.CharField(max_length=255)
    password = models.CharField(max_length=255)
    bindMode = models.CharField(
        max_length=11,
        choices=BIND_MODE_CHOICES,
        default="TRANSMITTER",
    )
    sourceTON = models.IntegerField()
    destTON = models.IntegerField()
    sourceNPI = models.IntegerField()
    destNPI = models.IntegerField()
    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="connectivity_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="connectivity_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.smppHost
