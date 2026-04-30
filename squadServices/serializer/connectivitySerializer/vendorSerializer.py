from squadServices.models.connectivityModel.verdor import Vendor
from squadServices.models.country import Country, Currency, Entity, State, TimeZone
from rest_framework import serializers


class VendorSerializer(serializers.ModelSerializer):
    companyName = serializers.CharField(source="company.name", read_only=True)
    smppName = serializers.CharField(source="smpp.smppHost", read_only=True)
    session = serializers.SerializerMethodField()

    class Meta:
        model = Vendor
        fields = [
            "id",
            "company",
            "companyName",
            "ratePlanName",
            "profileName",
            "invoicePolicy",
            "bindStatus",
            "smpp",
            "smppName",
            "connectionType",
            "session",
            "createdAt",
        ]

    def get_session(self, obj):
        # Count the currently ONLINE sessions for this specific client
        # We use 'active_sessions' because that is the related_name you set on ClientSession
        current_sessions = obj.sessions.filter(status="ONLINE").count()

        policy = getattr(obj, "policy", None)
        max_sessions = policy.maxSession if policy else 2
        # Format it nicely. (Handling the "0 = Unlimited" rule we set up earlier)
        if max_sessions == 0:
            return f"{current_sessions}/Unlimited"

        return f"{current_sessions}/{max_sessions}"
        # extra_kwargs = {"smppPassword": {"write_only": True}}
