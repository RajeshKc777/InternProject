import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Notification
from django.contrib.auth import get_user_model

User = get_user_model()

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        if self.scope["user"].is_anonymous:
            # Reject the connection
            await self.close()
        else:
            self.user = self.scope["user"]
            self.group_name = f'notifications_{self.user.id}'

            # Join notification group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()

    async def disconnect(self, close_code):
        # Leave notification group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        # For now, we do not expect to receive messages from client
        pass

    # Receive notification from group
    async def send_notification(self, event):
        notification = event['notification']

        # Send notification to WebSocket
        await self.send(text_data=json.dumps({
            'notification': notification
        }))

    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        try:
            notification = Notification.objects.get(id=notification_id, user=self.user)
            notification.is_read = True
            notification.save()
        except Notification.DoesNotExist:
            pass
