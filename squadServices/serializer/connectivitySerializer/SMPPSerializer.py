from squadServices.models.connectivityModel.smpp import SMPP
from squadServices.models.country import Country, Currency, Entity, State, TimeZone
from rest_framework import serializers


class SMPPSerializer(serializers.ModelSerializer):
    # countryName = serializers.CharField(source='country.name', read_only=True)

    class Meta:
        model = SMPP
        fields = [
            "id",
            "smppHost",
            "smppPort",
            "systemID",
            "bindMode",
            "password",
            "sourceTON",
            "sourceNPI",
            "destTON",
            "destNPI",
            "createdAt",
        ]
        # extra_kwargs = {"password": {"write_only": True}}
