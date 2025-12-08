from squadServices.models.connectivityModel.verdor import Vendor
from rest_framework import serializers

from squadServices.models.rateManagementModel.vendorRate import VendorRate


class VendorRateSerializer(serializers.ModelSerializer):
    countryName = serializers.CharField(source="country.name", read_only=True)
    timeZoneName = serializers.CharField(source="timeZone.name", read_only=True)

    class Meta:
        model = VendorRate
        fields = [
            "id",
            "country",
            "countryName",
            "ratePlan",
            "currencyCode",
            "countryCode",
            "MNC",
            "network",
            "dateTime",
            "timeZone",
            "timeZoneName",
            "country",
            "MCC",
            "rate",
            "remark",
        ]


# squadServices/serializers/vendor_rate_import_serializer.py


class VendorRateImportSerializer(serializers.ModelSerializer):
    class Meta:
        model = VendorRate
        fields = [
            "ratePlan",
            "network",
            "countryCode",
            "timeZone",
            "country",
            "MCC",
            "MNC",
            "rate",
            "remark",
            "dateTime",
        ]
