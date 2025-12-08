from squadServices.models.company import Company, CompanyCategory, CompanyStatus
from rest_framework import serializers

from squadServices.models.network import Network


class NetworkSerializer(serializers.ModelSerializer):
    countryName = serializers.CharField(source="country.name", read_only=True)

    class Meta:
        model = Network
        fields = ["id", "name", "countryName", "country", "MNC", "createdAt"]
