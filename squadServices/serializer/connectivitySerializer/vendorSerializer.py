from squadServices.models.connectivityModel.verdor import Vendor
from squadServices.models.country import Country, Currency, Entity, State, TimeZone
from rest_framework import serializers


class VendorSerializer(serializers.ModelSerializer):
    companyName = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = Vendor
        fields = ["id", "company", "companyName", "profileName", "connectionType"]
