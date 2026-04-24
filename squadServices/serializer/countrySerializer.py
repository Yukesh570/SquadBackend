from squadServices.models.country import Country, Currency, Entity, State, TimeZone
from rest_framework import serializers


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ["id", "iso2", "name", "region", "subRegion", "countryCode"]


class StateSerializer(serializers.ModelSerializer):
    countryName = serializers.CharField(source="country.name", read_only=True)

    class Meta:
        model = State
        fields = ["id", "name", "country", "countryName"]


class CurrencySerializer(serializers.ModelSerializer):

    class Meta:
        model = Currency
        fields = [
            "id",
            "name",
            "currencyCode",
            "numericCode",
            "symbol",
            "decimalPlaces",
            "isActive",
            "createdAt",
        ]


class EntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entity
        fields = [
            "id",
            "companyName",
            "legalEntityName",
            "invoiceNumber",
            "weekCommencing",
            "vatRegistrationNumber",
            "phone",
            "emailAddress",
            "businessAddress",
            "bankAccountDetail",
            "companyLogo",
            "isDeleted",
            "createdAt",
            "updatedAt",
        ]

        # Protects these fields from being modified by POST/PUT requests
        read_only_fields = ["id", "createdAt", "updatedAt", "createdBy", "updatedBy"]


class TimeZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeZone
        fields = ["id", "name"]
