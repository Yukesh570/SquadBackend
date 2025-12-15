from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models


class UserType(models.TextChoices):
    ADMIN = "ADMIN", "ADMIN"
    SALES = "SALES", "SALES"
    SUPPORT = "SUPPORT", "SUPPORT"
    NOC = "NOC", "NOC"
    RATE = "RATE", "RATE"
    FINANCE = "FINANCE", "FINANCE"


class User(AbstractUser):
    # Your existing fields
    phone = models.CharField(max_length=25, null=True, blank=True)
    userType = models.CharField(
        max_length=20, choices=UserType.choices, default="SALES"
    )
    isDeleted = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)


class UserLoginHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        related_name="loginHistory",
    )
    ipAddress = models.GenericIPAddressField(null=True, blank=True)
    browser = models.CharField(max_length=100, blank=True)
    device = models.CharField(max_length=100, blank=True)
    userAgent = models.TextField(blank=True)
    loggedAt = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-loggedAt"]

    def __str__(self):
        return f"{self.user.username} | {self.ipAddress} | {self.loggedAt}"
