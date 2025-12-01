from squadServices.models.connectivityModel.connectivity import Connectivity
from squadServices.models.country import Country, Currency, Entity, State, TimeZone
from rest_framework import serializers


class ConnectivitySerializer(serializers.ModelSerializer):
    # countryName = serializers.CharField(source='country.name', read_only=True)

    class Meta:
        model = Connectivity
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
