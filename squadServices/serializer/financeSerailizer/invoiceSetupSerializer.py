from rest_framework import serializers

from squadServices.models.finanace.invoiceSetup import InvoiceSetup


class InvoiceSetupSerializer(serializers.ModelSerializer):
    companyName = serializers.CharField(source="company.name", read_only=True)

    class Meta:
        model = InvoiceSetup
        fields = [
            "id",
            "company",
            "companyName",
            "billingAddressOverride",
            "businessEntity",
            "invoiceFrequency",
            "dueDays",
            "isTaxApplied",
            "tax",
            "createdAt",
        ]
