from django.conf import settings
from django.db import models

class EmailHost(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_hosts')
    name = models.CharField(max_length=100)  # User-friendly name
    smtpHost = models.CharField(max_length=255)
    smtpPort = models.IntegerField(default=587)
    smtpUser = models.CharField(max_length=255)
    smtpPassword = models.CharField(max_length=255)
    useTls = models.BooleanField(default=True)
    def __str__(self):
        return self.name
