from squadServices.models.clientModel.client import Client, IpWhitelist, PuskarClient

from rest_framework import serializers


class ClientSerializer(serializers.ModelSerializer):
    companyName = serializers.CharField(source="company.name", read_only=True)
    session = serializers.SerializerMethodField()

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
            "session",
            "createdAt",
        ]
        read_only_fields = [
            "bindStatus",
        ]
        # ⚡️ 3. Write the logic to calculate "Current/Max"

    def get_session(self, obj):
        # Count the currently ONLINE sessions for this specific client
        # We use 'active_sessions' because that is the related_name you set on ClientSession
        current_sessions = obj.active_sessions.filter(status="ONLINE").count()

        # Safely grab the maxSessions from the policy
        # If the client doesn't have a policy yet, fallback to your model's default of 2
        if hasattr(obj, "clientPolicy") and obj.clientPolicy:
            max_sessions = obj.clientPolicy.maxSessions
        else:
            max_sessions = 2

        # Format it nicely. (Handling the "0 = Unlimited" rule we set up earlier)
        if max_sessions == 0:
            return f"{current_sessions}/Unlimited"

        return f"{current_sessions}/{max_sessions}"
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
