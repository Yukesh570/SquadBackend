from rest_framework import serializers


from squadServices.models.transaction.transaction import (
    ClientTransaction,
    VendorTransaction,
)


class ClientTransactionSerializer(serializers.ModelSerializer):
    clientName = serializers.ReadOnlyField(source="client.name")

    # Use ReadOnlyField; if vendor is None, this returns None instead of crashing/disappearing
    message_id = serializers.ReadOnlyField(source="message.message_id")

    class Meta:
        model = ClientTransaction
        fields = [
            "id",
            "client",
            "clientName",
            "message",
            "message_id",
            "transactionType",
            "segments",
            "ratePerSegment",
            "amount",
            "balanceSpent",
            "description",
            "createdAt",
        ]


class VendorTransactionSerializer(serializers.ModelSerializer):
    vendorProfileName = serializers.ReadOnlyField(source="vendor.profileName")

    # Use ReadOnlyField; if vendor is None, this returns None instead of crashing/disappearing
    message_id = serializers.ReadOnlyField(source="message.message_id")

    # Use ReadOnlyField for smpp as well

    class Meta:
        model = VendorTransaction
        fields = [
            "id",
            "vendor",
            "vendorProfileName",
            "message",
            "message_id",
            "transactionType",
            "segments",
            "ratePerSegment",
            "amount",
            "balanceSpent",
            "description",
            "createdAt",
        ]
