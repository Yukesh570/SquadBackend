from rest_framework import serializers

from squadServices.models.email import EmailHost


class EmailHostSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailHost
        fields = ['id', 'name', 'smtpHost', 'smtpPort', 'smtpUser', 'smtpPassword', 'useTls']
        extra_kwargs = {
            'smtp_password': {'write_only': True}
        }
