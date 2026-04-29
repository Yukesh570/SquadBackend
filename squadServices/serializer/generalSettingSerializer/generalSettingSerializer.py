from rest_framework import serializers

from squadServices.models.generalSetting.generalSetting import GeneralSetting


class GeneralSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneralSetting
        fields = [
            "id",
            "companyName",
            "defaultLanguage",
            "defaultTimezone",
            "dateFormat",
            "datetimeFormat",
            "baseCurrency",
            "updatedBy",
            "updatedAt",
        ]
        # Protect these fields from being modified directly via the API payload
        read_only_fields = ["id", "updatedAt", "updatedBy"]
