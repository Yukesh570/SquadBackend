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
