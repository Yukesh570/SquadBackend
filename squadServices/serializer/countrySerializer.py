

from squadServices.models.country import Country, Currency, Entity, State, TimeZone
from rest_framework import serializers


class CountrySerializer(serializers.ModelSerializer):
    class Meta:
        model = Country
        fields = ['id', 'name', 'countryCode', 'MCC']



class StateSerializer(serializers.ModelSerializer):
    countryName = serializers.CharField(source='country.name', read_only=True)

    class Meta:
        model = State
        fields = ['id', 'name', 'country','countryName']


class CurrencySerializer(serializers.ModelSerializer):
    countryName = serializers.CharField(source='country.name', read_only=True)

    class Meta:
        model = Currency
        fields = ['id', 'name', 'country','countryName']

class EntitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Entity
        fields = ['id', 'name']

class TimeZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeZone
        fields = ['id', 'name']
    
