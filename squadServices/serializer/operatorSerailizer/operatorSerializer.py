from squadServices.models.connectivityModel.verdor import Vendor
from rest_framework import serializers
from squadServices.models.operators.operators import OperatorNetworkCode, Operators


class OperatorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Operators
        fields = [
            "id",
            "name",
            "country",
            "operatorCode",
            "status",
            "notes",
            "createdAt",
        ]


class OperatorNetworkCodeSerializer(serializers.ModelSerializer):
    # 🟢 Read-only fields to show "Human Readable" data to the frontend
    operator_name = serializers.ReadOnlyField(source="operator.operator_name")
    country_name = serializers.ReadOnlyField(source="country.name")
    country_iso = serializers.ReadOnlyField(source="country.iso2")

    class Meta:
        model = OperatorNetworkCode
        fields = [
            "id",
            "operator",
            "operator_name",
            "country",
            "country_name",
            "country_iso",
            "MCC",
            "MNC",
            "networkName",
            "networkType",
            "isPrimary",
            "status",
            "effectiveFrom",
            "effectiveTo",
            "notes",
            "createdAt",
        ]
        # Prevents the API from allowing manual updates to timestamps
        read_only_fields = ["createdAt"]
