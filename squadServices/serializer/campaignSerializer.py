# app/serializers.py
from rest_framework import serializers
from squadServices.models.campaign import Campaign, CampaignContact, Template


class CampaignSerializer(serializers.ModelSerializer):
    clientName = serializers.CharField(source="client.name", read_only=True)

    class Meta:
        model = Campaign
        fields = [
            "id",
            "name",
            "client",
            "clientName",
            "objective",
            "content",
            "template",
            "schedule",
        ]


class CampaignContactSerializer(serializers.ModelSerializer):
    campaign_name = serializers.CharField(source="campaign.name", read_only=True)

    class Meta:
        model = CampaignContact
        fields = ["id", "campaign_name", "contactNumber"]


class TemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ["id", "name", "content"]
