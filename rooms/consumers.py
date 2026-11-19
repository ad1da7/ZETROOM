import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_uuid = str(self.scope['url_route']['kwargs']['room_uuid'])
        self.room_group_name = f'room_{self.room_uuid}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)

        if data.get('type') == 'video_sync':
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'video_sync_message', 'data': data}
            )
        elif data.get('message'):
            username = data.get('username', 'Гость')
            message_text = data.get('message', '').strip()

            if message_text:
                await self.save_message(self.room_uuid, username, message_text)
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'room_message',
                        'data': {
                            'message': message_text,
                            'username': username
                        }
                    }
                )

    @database_sync_to_async
    def save_message(self, room_uuid, username, text):
        room = Room.objects.filter(uuid=room_uuid).first()
        if room:
            Message.objects.create(room=room, user=username, text=text)

    async def room_message(self, event):
        await self.send(text_data=json.dumps(event['data']))

    async def video_sync_message(self, event):
        await self.send(text_data=json.dumps(event['data']))
