from rest_framework import serializers

from squadServices.models.smpp.smppSMS import SMSMessage


class smppSMSSerializer(serializers.ModelSerializer):
    clientName = serializers.ReadOnlyField(source="client.name")

    # Use ReadOnlyField; if vendor is None, this returns None instead of crashing/disappearing
    vendorName = serializers.ReadOnlyField(source="vendor.profileName")

    # Use ReadOnlyField for smpp as well
    smppName = serializers.ReadOnlyField(source="smpp.systemID")

    class Meta:
        model = SMSMessage
        fields = [
            "id",
            "destination",
            "text",
            "status",
            "encoding",
            "segmentNumber",
            "characterCount",
            "clientName",
            "vendorName",
            "smppName",
            "message_id",
            "systemId",
            "createdAt",
        ]
