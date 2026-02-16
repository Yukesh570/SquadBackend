from rest_framework import serializers

from squadServices.models.users import UserLog


class UserLogSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = UserLog
        fields = ["id", "username", "user", "title", "action", "createdAt"]
        read_only_fields = ["user"]
