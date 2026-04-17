from squadServices.models.clientModel.client import Client, IpWhitelist, PuskarClient

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
            "bindStatus",
            "route",
            "paymentTerms",
            "creditLimit",
            "invoicePolicy",
            "balanceAlertAmount",
            "allowNetting",
            "ipWhitelist",
            "enableDlr",
            "smppUsername",
            "smppPassword",
            "internalNotes",
            "createdAt",
        ]
        read_only_fields = [
            "bindStatus",
        ]
        # extra_kwargs = {"smppPassword": {"write_only": True}}


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


class PuskarClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = PuskarClient
        fields = [
            "id",
            "name",
            "DsmppUsername",
            "FsmppUsername",
            "smppPassword",
            "createdAt",
        ]
        read_only_fields = [
            "DsmppUsername",
            "FsmppUsername",
            "smppPassword",
        ]
