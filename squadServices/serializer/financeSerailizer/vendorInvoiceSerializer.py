from rest_framework import serializers
from squad import settings
from squadServices.models.finanace.invoice import VendorInvoice


class VendorInvoiceSerializer(serializers.ModelSerializer):
    # 1. Make the Vendor ID human-readable for your React tables
    vendorName = serializers.CharField(source="vendor.profileName", read_only=True)

    accountManagerName = serializers.CharField(
        source="accountManager.username", read_only=True, default="Unassigned"
    )

    # 3. Create a custom field that gives React the exact URL to download the PDF
    downloadUrl = serializers.SerializerMethodField()

    class Meta:
        model = VendorInvoice
        fields = [
            "id",
            "accountManager",
            "accountManagerName",
            "invoiceNumber",
            "vendor",
            "vendorName",
            "billingPeriodStart",
            "billingPeriodEnd",
            "invoiceDate",
            "totalAmount",
            "totalSegments",
            "status",
            "invoicePdf",
            "downloadUrl",
            "createdAt",
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
            return (
                f"{settings.BACKEND_API}/api/finance/vendor-invoice/{obj.id}/download/"
            )
        return None
