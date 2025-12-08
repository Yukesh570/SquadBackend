from squadServices.models.connectivityModel.verdor import Vendor
from rest_framework import serializers

from squadServices.models.rateManagementModel.customerRate import CustomerRate


class CustomerRateSerializer(serializers.ModelSerializer):
    countryName = serializers.CharField(source="country.name", read_only=True)
    timeZoneName = serializers.CharField(source="timeZone.name", read_only=True)

    class Meta:
        model = CustomerRate
        fields = [
            "id",
            "country",
            "countryName",
            "ratePlan",
            "currencyCode",
            "countryCode",
            "MNC",
            "dateTime",
            "timeZone",
            "timeZoneName",
            "country",
            "MCC",
            "rate",
            "remark",
        ]
