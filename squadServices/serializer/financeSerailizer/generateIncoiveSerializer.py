from rest_framework import serializers
from django.contrib.auth import get_user_model

from squadServices.models.clientModel.client import Client
from squadServices.models.connectivityModel.verdor import Vendor

# Adjust imports based on your structure
# from squadServices.models.client import Client

User = get_user_model()


class GenerateClientInvoiceRequestSerializer(serializers.Serializer):
    """
    This does NOT save to the database directly.
    It just validates the data coming from the frontend form.
    """

    # 1. Account Manager (AM) (Selection)
    accountManager = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    # 2. Client (Selection)
    client = serializers.PrimaryKeyRelatedField(
        queryset=Client.objects.all()  # Assuming you have a Client model
    )

    # 3. From Date
    fromDate = serializers.DateField()

    # 4. To Date
    toDate = serializers.DateField()

    # 5. Invoice Date
    invoiceDate = serializers.DateField()

    def validate(self, data):
        """Ensure the From Date is before the To Date"""
        if data["fromDate"] > data["toDate"]:
            raise serializers.ValidationError(
                {"toDate": "To Date cannot be earlier than From Date."}
            )
        return data


class GenerateVendorInvoiceRequestSerializer(serializers.Serializer):
    """
    This does NOT save to the database directly.
    It just validates the data coming from the frontend form.
    """

    # 1. Account Manager (AM) (Selection)
    accountManager = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(), required=False, allow_null=True
    )

    # 2. Vendor (Selection)
    vendor = serializers.PrimaryKeyRelatedField(
        queryset=Vendor.objects.all()  # Assuming you have a Vendor model
    )

    # 3. From Date
    fromDate = serializers.DateField()

    # 4. To Date
    toDate = serializers.DateField()

    # 5. Invoice Date
    invoiceDate = serializers.DateField()

    def validate(self, data):
        """Ensure the From Date is before the To Date"""
        if data["fromDate"] > data["toDate"]:
            raise serializers.ValidationError(
                {"toDate": "To Date cannot be earlier than From Date."}
            )
        return data
