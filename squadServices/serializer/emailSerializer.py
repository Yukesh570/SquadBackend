from rest_framework import serializers

from squadServices.models.email import EmailHost, EmailTemplate
from django.db import IntegrityError


class EmailHostSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailHost
        fields = ['id', 'name', 'smtpHost', 'smtpPort', 'smtpUser', 'smtpPassword', 'security']
        extra_kwargs = {
            'smtp_password': {'write_only': True}
        }
    
class EmailTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailTemplate
        fields = ['id', 'name', 'content']