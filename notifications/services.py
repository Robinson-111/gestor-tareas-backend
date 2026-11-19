from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone

from notifications.models import Notification


def user_group_name(user_id: int) -> str:
    return f'user_{user_id}'


def serialize_notification(notification: Notification) -> dict:
    return {
        'id': notification.id,
        'type': notification.type,
        'title': notification.title,
        'message': notification.message,
        'payload': notification.payload,
        'is_read': notification.is_read,
        'created_at': notification.created_at.isoformat(),
    }


def _push(user_id: int, notification: Notification, unread: int) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        user_group_name(user_id),
        {
            'type': 'notification.message',
            'notification': serialize_notification(notification),
            'unread_count': unread,
        }
    )


def notify(
    user,
    type: str,
    title: str,
    message: str = '',
    payload: dict | None = None
) -> Notification:
    """
    Crea la notificación y la empuja por WebSocket al destinatario.

    El push se difiere a `on_commit` para no notificar cambios que la
    transacción termine revirtiendo.
    """
    notification = Notification.objects.create(
        user=user,
        type=type,
        title=title,
        message=message,
        payload=payload or {},
    )

    unread = unread_count(user)
    transaction.on_commit(
        lambda: _push(user.id, notification, unread)
    )

    return notification


def notify_many(
    users,
    type: str,
    title: str,
    message: str = '',
    payload: dict | None = None,
    exclude_user_ids=(),
) -> list[Notification]:
    """
    Notifica a varios usuarios, omitiendo duplicados y destinatarios excluidos.
    """
    excluded = set(exclude_user_ids)
    seen = set()
    created = []

    for user in users:
        if user is None or user.id in excluded or user.id in seen:
            continue
        seen.add(user.id)
        created.append(notify(user, type, title, message, payload))

    return created


def get_notifications(user, unread: bool | None = None):
    queryset = Notification.objects.filter(user=user)

    if unread is True:
        queryset = queryset.filter(is_read=False)
    elif unread is False:
        queryset = queryset.filter(is_read=True)

    return queryset


def unread_count(user) -> int:
    return Notification.objects.filter(user=user, is_read=False).count()


def mark_read(user, notification_id: int) -> Notification:
    notification = get_object_or_404(
        Notification, id=notification_id, user=user
    )

    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])

    return notification


def mark_all_read(user) -> int:
    return Notification.objects.filter(
        user=user, is_read=False
    ).update(is_read=True)


def delete_notification(user, notification_id: int) -> Notification:
    """
    Elimina una notificación propia del usuario autenticado.
    """
    notification = get_object_or_404(
        Notification, id=notification_id, user=user
    )

    notification.delete()

    return notification


def delete_all_notifications(user) -> int:
    """
    Elimina todas las notificaciones del usuario autenticado.
    """
    return Notification.objects.filter(user=user).delete()[0]


def cleanup_read_notifications(user=None, days: int = 3) -> int:
    """
    Elimina notificaciones leídas con más de `days` días de antigüedad.

    Si se envía un `user`, solo se limpian las notificaciones de ese
    usuario; si no, la retención se aplica a todas las leídas del sistema.
    """
    cutoff = timezone.now() - timedelta(days=days)
    queryset = Notification.objects.filter(
        is_read=True,
        created_at__lt=cutoff,
    )

    if user is not None:
        queryset = queryset.filter(user=user)

    return queryset.delete()[0]
