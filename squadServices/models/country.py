from django.conf import settings
from django.db import models


class Country(models.Model):
    name = models.CharField(max_length=100)  # User-friendly name
    countryCode = models.CharField(max_length=100)
    MCC = models.IntegerField()
    isDeleted = models.BooleanField(default=False)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="countries_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="countries_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class State(models.Model):
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="states"
    )
    name = models.CharField(max_length=100)  # User-friendly name
    isDeleted = models.BooleanField(default=False)

    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="states_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="states_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class Currency(models.Model):
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE, related_name="currencies"
    )
    name = models.CharField(max_length=100)
    isDeleted = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="currency_created",
    )
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="currency_updated",
    )

    def __str__(self):
        return self.name


class Entity(models.Model):
    name = models.CharField(max_length=100)
    isDeleted = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="entities_created",
    )
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="entities_updated",
    )

    def __str__(self):
        return self.name


class TimeZone(models.Model):
    name = models.CharField(max_length=100)
    isDeleted = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="timeZone_created",
    )
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="timeZone_updated",
    )

    def __str__(self):
        return self.name
