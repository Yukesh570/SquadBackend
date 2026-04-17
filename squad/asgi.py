"""
ASGI config for squad project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
import squadServices.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "squad.settings")

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": URLRouter(squadServices.routing.websocket_urlpatterns),
    }
)
