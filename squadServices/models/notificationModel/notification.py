from django.conf import settings
from django.db import models


class Notification(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()

    isDeleted = models.BooleanField(default=False)
    createdAt = models.DateTimeField(auto_now_add=True)
    updatedAt = models.DateTimeField(auto_now=True)
    createdBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="notification_created",
    )
    updatedBy = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="notification_updated",
    )

    class Meta:
        ordering = ["-updatedAt"]

    def __str__(self):
        return self.title
