from rest_framework import serializers, generics
from decimal import Decimal
from squadServices.helper.pagination import StandardResultsSetPagination
from squadServices.models.detailedReport.detailedReport import DetailedSMSReport

# Import your pagination class


class DetailedReportSerializer(serializers.ModelSerializer):
    # 'source' removed because it matches the variable name
    client = serializers.CharField(read_only=True)
    clientRate = serializers.DecimalField(
        max_digits=12, decimal_places=6, read_only=True
    )
    client_charge = serializers.DecimalField(
        max_digits=12, decimal_places=6, read_only=True
    )

    vendor = serializers.CharField(read_only=True)
    vendorRate = serializers.DecimalField(
        max_digits=12, decimal_places=6, read_only=True
    )
    vendor_charge = serializers.DecimalField(
        max_digits=12, decimal_places=6, read_only=True
    )

    margin = serializers.SerializerMethodField()
    content = serializers.CharField(
        source="text", read_only=True
    )  # Keep this: name 'content' != source 'text'
    submitStatus = serializers.CharField(read_only=True)

    request_time = serializers.DateTimeField(format="%d-%m-%Y %H:%M:%S", read_only=True)

    senderId = serializers.CharField(read_only=True)
    part_total = serializers.IntegerField(read_only=True)

    class Meta:
        model = DetailedSMSReport
        fields = [
            "id",
            "client",
            "destination",
            "clientRate",
            "client_charge",
            "part_total",
            "senderId",
            "vendor",
            "vendorRate",
            "vendor_charge",
            "margin",
            "content",
            "submitStatus",
            "request_time",
            "text_message_id",
            "vendor_msg_id",
        ]

    def get_margin(self, obj):
        client_cost = obj.client_charge or Decimal("0.000000")
        vendor_cost = obj.vendor_charge or Decimal("0.000000")
        return float(client_cost - vendor_cost)
