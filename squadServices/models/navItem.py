from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

from squad import settings


class NavItem(models.Model):
    label = models.CharField(max_length=50)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True)
    url = models.CharField(max_length=200)
    order = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)
    icon = models.CharField(max_length=50, default="Home")
    isDeleted = models.BooleanField(default=False)

    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="navItem_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="navItem_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        return self.label


class NavUserRelation(models.Model):
    userType = models.CharField(max_length=50)
    navigateId = models.ForeignKey(
        NavItem, on_delete=models.CASCADE, related_name="navigate"
    )
    read = models.BooleanField(default=False)
    write = models.BooleanField(default=False)
    delete = models.BooleanField(default=False)
    put = models.BooleanField(default=False)

    def __str__(self):
        return self.userType
