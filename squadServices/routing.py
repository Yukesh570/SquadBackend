# squadServices/routing.py
from django.urls import re_path

from squadServices import consumers

websocket_urlpatterns = [
    # The ^ means "starts exactly here", preventing accidental URL mismatches
    re_path(r"^ws/status/$", consumers.DashboardConsumer.as_asgi()),
]
