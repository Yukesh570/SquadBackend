from squadServices.models.connectivityModel.verdor import Vendor
from rest_framework import serializers
from squadServices.models.operators.operators import Operators


class OperatorSerializer(serializers.ModelSerializer):

    class Meta:
        model = Operators
        fields = [
            "id",
            "name",
            "country",
            "MNC",
            "createdAt",
        ]
