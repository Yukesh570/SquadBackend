
from squadServices.models.connectivity.connectivity import Connectivity
from squadServices.models.connectivity.verdor import Vendor
from squadServices.models.country import Country, Currency, Entity, State, TimeZone
from rest_framework import serializers



class VendorSerializer(serializers.ModelSerializer):
    countryName = serializers.CharField(source='country.name', read_only=True)

    class Meta:
        model = Vendor
        fields = ['id', 'company','companyName','profileName', 'connectionType']
    