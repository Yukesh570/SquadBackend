from django.db import models

from squad import settings


class objectiveType(models.TextChoices):
    Promotion = "Promotion"
    Announcement = "Announcement"
    Re_engagement = "Re-engagement"


class Template(models.Model):
    name = models.CharField(max_length=100, unique=True)
    content = models.TextField()
    isDeleted = models.BooleanField(default=False)

    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="template_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="template_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        return self.name


class Campaign(models.Model):
    name = models.CharField(max_length=100)
    objective = models.CharField(max_length=20, choices=objectiveType.choices)
    content = models.TextField(null=True, blank=True)
    template = models.ForeignKey(
        Template, on_delete=models.SET_NULL, null=True, blank=True
    )

    schedule = models.DateTimeField(null=True, blank=True)
    isDeleted = models.BooleanField(default=False)

    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="campaign_created",
    )
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="campaign_updated",
    )
    updatedAt = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        return self.name


class CampaignContact(models.Model):
    campaign = models.ForeignKey(
        Campaign, on_delete=models.CASCADE, related_name="contacts"
    )
    contactNumber = models.CharField(max_length=20)

    def __str__(self):
        return self.contactNumber
