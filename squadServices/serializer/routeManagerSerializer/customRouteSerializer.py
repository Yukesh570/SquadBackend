from rest_framework import serializers

from squadServices.models.routeManager.customRoute import CustomRoute


class CustomRouteSerializer(serializers.ModelSerializer):
    orginatingCompanyName = serializers.CharField(
        source="orginatingCompany.name", read_only=True
    )
    orginatingClientName = serializers.CharField(
        source="orginatingClient.name", read_only=True
    )
    countryName = serializers.CharField(source="country.name", read_only=True)
    operatorName = serializers.CharField(source="operator.name", read_only=True)
    terminatingCompanyName = serializers.CharField(
        source="terminatingCompany.name", read_only=True
    )
    terminatingVendorProfileName = serializers.CharField(
        source="terminatingVendor.profileName", read_only=True
    )

    class Meta:
        model = CustomRoute
        fields = [
            "id",
            "name",
            "country",
            "operator",
            "orginatingCompany",
            "orginatingClient",
            "terminatingCompany",
            "terminatingVendor",
            "orginatingCompanyName",
            "orginatingClientName",
            "countryName",
            "operatorName",
            "terminatingCompanyName",
            "terminatingVendorProfileName",
            "priority",
            "status",
            "createdAt",
        ]
