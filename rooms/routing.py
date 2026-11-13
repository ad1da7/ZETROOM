from django.urls import path
from . import consumers

#пути для websocket подключений
websocket_urlpatterns = [
    path('ws/room/<uuid:room_uuid>/', consumers.ChatConsumer.as_asgi()),
]
