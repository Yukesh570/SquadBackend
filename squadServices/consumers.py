# squadServices/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer


class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # When a frontend browser connects, add them to the "dashboard_updates" group
        self.group_name = "dashboard_updates"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # When the browser closes, remove them from the group
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    # This function is triggered whenever your SMPP server broadcasts a message!
    async def status_change(self, event):
        # Grab the data sent from the SMPP server
        username = event["username"]
        new_status = event["status"]

        # Push it down the WebSocket to the React frontend
        await self.send(
            text_data=json.dumps({"username": username, "status": new_status})
        )

    # Catches the 'session_change' event from the SMPP server
    async def session_change(self, event):
        # Send message to WebSocket (Frontend)
        await self.send(
            text_data=json.dumps(
                {
                    "action": "session_update",  # Tell the frontend JS what to do
                    "session": {
                        "id": event["session_id"],
                        "systemId": event["system_id"],
                        "ip": event["ip"],
                        "port": event["port"],
                        "bindType": event["bind_type"],
                        "status": event["status"],
                    },
                }
            )
        )
