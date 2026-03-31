from rest_framework import serializers

from squadServices.models.finanace.invoiceSetup import InvoiceSetup


class InvoiceSetupSerializer(serializers.ModelSerializer):
    companyName = serializers.CharField(source="company.name", read_only=True)
    businessEntityName = serializers.CharField(
        source="businessEntity.legalEntityName", read_only=True
    )

    class Meta:
        model = InvoiceSetup
        fields = [
            "id",
            "company",
            "companyName",
            "billingAddressOverride",
            "businessEntity",
            "businessEntityName",
            "invoiceFrequency",
            "dueDays",
            "isTaxApplied",
            "tax",
            "createdAt",
        ]
