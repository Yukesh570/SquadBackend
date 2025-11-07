# app/serializers.py
from rest_framework import serializers
from squadServices.models.campaign import Campaign, Template

class CampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campaign
        fields = ['id', 'name', 'objective', 'content', 'template','schedule']

class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ['id', 'name', 'content']




