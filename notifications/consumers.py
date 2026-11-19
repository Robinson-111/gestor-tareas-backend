from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from notifications.services import unread_count, user_group_name


class NotificationConsumer(AsyncJsonWebsocketConsumer):
    """
    Canal personal de notificaciones.

    - Autenticación: JWT validado en el handshake (middleware).
    - Grupo: `user_<id>`, de modo que nadie puede suscribirse a otro usuario.
    - Mensajes de servidor:
        {"type": "unread_count", "count": n}
        {"type": "notification", "notification": {...}, "unread_count": n}
    - Mensajes de cliente: {"type": "ping"} → {"type": "pong"}
    """

    async def connect(self):
        user = self.scope.get('user')

        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.group_name = user_group_name(user.id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        subprotocol = self.scope.get('ws_subprotocol')
        if subprotocol:
            await self.accept(subprotocol=subprotocol)
        else:
            await self.accept()

        count = await database_sync_to_async(unread_count)(user)
        await self.send_json({'type': 'unread_count', 'count': count})

    async def disconnect(self, code):
        group_name = getattr(self, 'group_name', None)

        if group_name:
            await self.channel_layer.group_discard(
                group_name, self.channel_name
            )

    async def receive_json(self, content, **kwargs):
        if content.get('type') == 'ping':
            await self.send_json({'type': 'pong'})

    async def notification_message(self, event):
        await self.send_json({
            'type': 'notification',
            'notification': event['notification'],
            'unread_count': event['unread_count'],
        })
