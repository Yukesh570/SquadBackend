from django.conf import settings
from django.db import models
class securityType(models.TextChoices):
    SSL= "SSL"
    TLS = "TLS"
 
class EmailHost(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_hosts')
    name = models.CharField(max_length=100)  # User-friendly name
    smtpHost = models.CharField(max_length=255)
    smtpPort = models.IntegerField(default=587)
    smtpUser = models.CharField(max_length=255)
    smtpPassword = models.CharField(max_length=255)
    security = models.CharField(max_length=20, choices=securityType.choices,default="TLS")

    def __str__(self):
        return self.name
    
    class Meta:
        unique_together = ('smtpHost', 'smtpUser') 


class EmailTemplate(models.Model):
    
    name = models.CharField(max_length=100,unique=True)
    content = models.TextField()

    def __str__(self):
        return self.name