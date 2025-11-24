
from squadServices.models.connectivity.connectivity import Connectivity
from squadServices.models.country import Country, Currency, Entity, State, TimeZone
from rest_framework import serializers



class ConnectivitySerializer(serializers.ModelSerializer):
    # countryName = serializers.CharField(source='country.name', read_only=True)

    class Meta:
        model = Connectivity
        fields = ['id', 'smppHost', 'smppPort','systemID','bindMode','sourceTON','sourceNPI','destTON','destNPI']
        extra_kwargs = {
            'smtp_password': {'write_only': True}
        } 