from rest_framework import serializers

from squadServices.models.clientModel.client import ClientSession


class ClientSessionSerializer(serializers.ModelSerializer):
    # ⚡️ FRONTEND TRICK: Pull the client's username directly into this payload
    # so you don't have to make a second API call from React/Vue to get their name!
    clientUsername = serializers.CharField(source="client.smppUsername", read_only=True)
    companyName = serializers.CharField(
        source="client.company.name", read_only=True, default="Unknown"
    )

    class Meta:
        model = ClientSession
        fields = [
            "sessionId",
            "client",
            "clientUsername",
            "companyName",
            "systemId",
            "bindType",
            "remoteIp",
            "remotePort",
            "connectedAt",
            "boundAt",
            "last_activityAt",
            "status",
        ]

        # Lock it down! The dashboard should only view this data, never edit it.
        read_only_fields = fields
