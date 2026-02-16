from rest_framework import serializers

from squadServices.models.notificationModel.notification import Notification


class NotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Notification
        fields = ["id", "title", "description", "createdAt"]
