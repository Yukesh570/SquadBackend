from rest_framework import serializers

from squadServices.models.smpp.smppSMS import (
    DLREvent,
    MessageAttempt,
    MessageAuditLog,
    SMSMessage,
    SMSMessagePart,
)


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


class SMSMessagePartSerializer(serializers.ModelSerializer):
    # Optional: If you want to see the parent message ID and destination easily
    parent_message_destination = serializers.CharField(
        source="message.destination", read_only=True
    )

    class Meta:
        model = SMSMessagePart
        fields = "__all__"
        # BinaryFields (like short_message) can cause JSON serialization issues.
        # DRF usually encodes them as base64, but it's safest to make them read-only
        # so clients don't accidentally corrupt the UDH bytes when doing PUT/PATCH requests.
        read_only_fields = ("short_message", "created_at", "updated_at")


class MessageAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttempt
        fields = "__all__"
        read_only_fields = ("started_at", "request_payload", "response_payload")


class DLREventSerializer(serializers.ModelSerializer):
    class Meta:
        model = DLREvent
        fields = "__all__"
        read_only_fields = ("received_at", "raw_payload")


class MessageAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAuditLog
        fields = "__all__"
        # Audit logs should NEVER be editable via API
        read_only_fields = (
            "message",
            "segment",
            "from_status",
            "to_status",
            "changed_by",
            "reason",
            "changed_at",
        )
