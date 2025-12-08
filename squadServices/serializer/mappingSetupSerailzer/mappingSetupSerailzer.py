from squadServices.models.connectivityModel.verdor import Vendor
from rest_framework import serializers

from squadServices.models.mappingSetup.mappingSetup import MappingSetup


class MappingSetupSerializer(serializers.ModelSerializer):

    class Meta:
        model = MappingSetup
        fields = [
            "id",
            "ratePlan",
            "country",
            "countryCode",
            "timeZone",
            "network",
            "MCC",
            "MNC",
            "rate",
            "dateTime",
            "createdAt",
        ]
