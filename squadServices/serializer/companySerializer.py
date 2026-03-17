from squadServices.models.company import Company, CompanyCategory, CompanyStatus
from rest_framework import serializers


class CompanyCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyCategory
        fields = ["id", "name"]


class CompanyStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = CompanyStatus
        fields = ["id", "name"]


class CompanySerializer(serializers.ModelSerializer):
    statusName = serializers.CharField(source="status.name", read_only=True)
    countryName = serializers.CharField(source="country.name", read_only=True)
    currencyCode = serializers.CharField(source="currency.code", read_only=True)

    # woooorrrrkkkkiiiinnng
    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "shortName",
            "phone",
            "companyEmail",
            "supportEmail",
            "billingEmail",
            "ratesEmail",
            "lowBalanceAlertEmail",
            "country",
            "state",
            "category",
            "status",
            "statusName",
            "currencyCode",
            "countryName",
            "currency",
            "timeZone",
            "businessEntity",
            "customerCreditLimit",
            "vendorCreditLimit",
            "balanceAlertAmount",
            "referencNumber",
            "vatNumber",
            "address",
            "validityPeriod",
            "defaultEmail",
            "onlinePayment",
            "companyBlocked",
            "allowWhiteListedCards",
            "sendDailyReports",
            "allowNetting",
            "showHlrApi",
            "enableVendorPanel",
            "createdAt",
        ]
