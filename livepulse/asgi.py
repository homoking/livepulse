import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "livepulse.settings")

django_asgi_app = get_asgi_application()

from lipapp.consumers import RoomConsumer  # ⬅️ بعد از setdefault

websocket_urlpatterns = [
    path("ws/room/<slug:slug>/", RoomConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": URLRouter(websocket_urlpatterns),
})
