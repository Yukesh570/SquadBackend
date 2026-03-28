from squadServices.models.finanace.invoice import ClientInvoice
from rest_framework import serializers
from squad import settings


class ClientInvoiceSerializer(serializers.ModelSerializer):
    # 1. Make the Client ID human-readable for your React tables
    clientName = serializers.CharField(source="client.name", read_only=True)

    # 2. Show who generated it (falls back to "System" if no user is attached)
    createdByName = serializers.CharField(
        source="createdBy.get_full_name", read_only=True, default="System"
    )

    # 3. Create a custom field that gives React the exact URL to download the PDF
    downloadUrl = serializers.SerializerMethodField()

    class Meta:
        model = ClientInvoice
        fields = [
            "id",
            "invoiceNumber",
            "client",
            "clientName",
            "billingPeriodStart",
            "billingPeriodEnd",
            "invoiceDate",
            "totalAmount",
            "status",
            "invoicePdf",
            "downloadUrl",
            "createdAt",
            "createdByName",
        ]

        # Protect financial data! The frontend should NEVER be able to
        read_only_fields = [
            "invoiceNumber",
            "totalAmount",
            "invoicePdf",
        ]

    def get_downloadUrl(self, obj):
        """
        Dynamically generates the download link using the API endpoint we created.
        Returns null if the Celery task hasn't finished making the PDF yet.
        """
        if obj.invoicePdf and obj.invoicePdf.name:
            return f"{settings.BACKEND_API}/api/finance/invoice/{obj.id}/download/"
        return None
