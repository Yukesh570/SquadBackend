from squadServices.models.clientModel.client import Client

from rest_framework import serializers


class ClientSerializer(serializers.ModelSerializer):
    companyName = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Client
        fields = [
            "id",
            "company",
            "companyName",
            "name",
            "status",
            "route",
            "paymentTerms",
            "creditLimit",
            "balanceAlertAmount",
            "allowNetting",
            "ipWhitelist",
            "smppUsername",
            "smppPassword",
            "internalNotes",
            "createdAt",
        ]
        # extra_kwargs = {"smppPassword": {"write_only": True}}
