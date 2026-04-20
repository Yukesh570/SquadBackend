from rest_framework import serializers

from squadServices.models.clientModel.client import ClientPolicy
from squadServices.models.connectivityModel.verdor import VendorPolicy


class VendorPolicySerializer(serializers.ModelSerializer):
    # Pulls the Vendor's string name so your frontend can display it easily
    vendor_name = serializers.CharField(source="vendor.profileName", read_only=True)

    class Meta:
        model = VendorPolicy
        fields = "__all__"
        # Protect your audit logs from being modified via API requests
        read_only_fields = ["createdAt", "updatedAt", "createdBy", "updatedBy"]


class ClientPolicySerializer(serializers.ModelSerializer):
    # Pulls the Client's string name for easy frontend rendering
    client_name = serializers.CharField(source="client.name", read_only=True)

    class Meta:
        model = ClientPolicy
        fields = "__all__"
        # Protect your audit logs from being modified via API requests
        read_only_fields = ["createdAt", "updatedAt", "createdBy", "updatedBy"]
