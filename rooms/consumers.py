import json
from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_uuid = str(self.scope['url_route']['kwargs']['room_uuid'])
        self.room_group_name = f'room_{self.room_uuid}'
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)

        if text_data_json.get('type') == 'video_sync':
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'video_sync_message', 'data': text_data_json}
            )
        else:
            await self.channel_layer.group_send(
                self.room_group_name,
                {'type': 'room_message', 'data': text_data_json}
            )

    async def room_message(self, event):
        await self.send(text_data=json.dumps(event['data']))

    async def video_sync_message(self, event):
        await self.send(text_data=json.dumps(event['data']))