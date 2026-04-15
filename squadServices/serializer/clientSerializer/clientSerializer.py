from squadServices.models.clientModel.client import Client, IpWhitelist

from rest_framework import serializers


class ClientSerializer(serializers.ModelSerializer):
    companyName = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Client
        fields = [
            "id",
            "company",
            "companyName",
            "ratePlanName",
            "name",
            "status",
            "route",
            "paymentTerms",
            "creditLimit",
            "balanceAlertAmount",
            "allowNetting",
            "ipWhitelist",
            "enableDlr",
            "smppUsername",
            "smppPassword",
            "internalNotes",
            "createdAt",
        ]
        # extra_kwargs = {"smppPassword": {"write_only": True}}


class PuskarClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            "id",
            "company",
            "ratePlanName",
            "name",
            "status",
            "route",
            "paymentTerms",
            "creditLimit",
            "balanceAlertAmount",
            "allowNetting",
            "ipWhitelist",
            "enableDlr",
            "smppUsername",
            "smppPassword",
            "internalNotes",
            "createdAt",
        ]

        # Tell DRF to completely ignore these fields during POST/PUT requests,
        # but still include them in the JSON response.
        read_only_fields = [
            "company",
            "ratePlanName",
            "status",
            "route",
            "paymentTerms",
            "creditLimit",
            "balanceAlertAmount",
            "allowNetting",
            "ipWhitelist",
            "enableDlr",
            "smppUsername",
            "smppPassword",
            "internalNotes",
        ]
        # Note: 'id' and 'createdAt' are automatically read-only by DRF,
        # so you don't even need to list them here!


class IpWhitelistSerializer(serializers.ModelSerializer):
    clientName = serializers.CharField(source="client.name", read_only=True)

    class Meta:
        model = IpWhitelist
        fields = [
            "id",
            "ip",
            "client",
            "clientName",
            "createdAt",
        ]
