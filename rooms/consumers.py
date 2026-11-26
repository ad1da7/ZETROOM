import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_uuid = str(self.scope['url_route']['kwargs']['room_uuid'])
        self.room_group_name = f'room_{self.room_uuid}'

        # Подключаемся к комнате
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'voice_signal_message',
                'data': {'type': 'voice_leave', 'sender': self.channel_name}
            }
        )
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type')

        # --- ЛОГИКА ДЛЯ СИГНАЛОВ ГОЛОСА ---
        if msg_type in ['voice_join', 'voice_offer', 'voice_answer', 'voice_ice', 'voice_leave']:
            # Добавляем отправителя
            data['sender'] = self.channel_name

            target = data.get('target')

            if target:
                # Если указан target, отправляем ТОЛЬКО этому пользователю
                # Для этого нужно знать его channel_name.
                # Но так как у нас нет прямой связи user_id -> channel_name,
                # мы используем группу комнаты, но с фильтром в voice_signal_message.
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {'type': 'voice_signal_message', 'data': data}
                )
            else:
                # Если target нет (например, voice_join), шлем всем
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {'type': 'voice_signal_message', 'data': data}
                )

        elif msg_type == 'video_sync':
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

    async def voice_signal_message(self, event):
        # --- ВОТ ГЛАВНЫЙ ФИКС ---
        # Не отправляем сигнал самому себе (по sender),
        # и если указан target в сообщении, проверяем, совпадает ли он с нашим channel_name
        sender = event['data'].get('sender')
        target = event['data'].get('target')

        # Если это мы отправили — не шлем обратно
        if sender == self.channel_name:
            return

        # Если есть target и он не равен нашему каналу — не шлем
        # ВНИМАНИЕ: В нашем фронтенде target — это user_id, а тут channel_name.
        # Но мы отправляем через group_send, и все получают.
        # Чтобы отфильтровать по user_id, нужно знать channel_name.

        # Самый простой способ для текущего кода:
        # Мы не можем отфильтровать по user_id в group_send без маппинга.
        # Поэтому мы просто отправляем всем, но в JS-коде добавим проверку!

        await self.send(text_data=json.dumps(event['data']))

    async def kick_signal_message(self, event):
        await self.send(text_data=json.dumps(event['data']))