from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from datetime import timedelta
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import AccessToken

from account.models import User
from config.asgi import application
from modules.models import Module, UserModule
from modules.services import (
    add_member_to_module,
    create_module,
    delete_member_from_module,
    edit_rol_member_from_module,
)
from notifications.middleware import SUBPROTOCOL
from notifications.models import Notification
from notifications.services import cleanup_read_notifications, notify
from tasks.models import Tasks
from tasks.services import create_task, delete_task, update_task

IN_MEMORY_LAYER = {
    'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}
}


class NotificationApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='notif@example.com', name='Notif', password='Password123'
        )
        self.other = User.objects.create_user(
            email='other.notif@example.com', name='Other', password='Password123'
        )
        self.mine = Notification.objects.create(
            user=self.user,
            type=Notification.Type.TASK_ASSIGNED,
            title='Mía',
            message='Primera',
        )
        self.mine_read = Notification.objects.create(
            user=self.user,
            type=Notification.Type.TASK_CREATED,
            title='Leída',
            is_read=True,
        )
        Notification.objects.create(
            user=self.other,
            type=Notification.Type.TASK_CREATED,
            title='Ajena',
        )

    def test_list_returns_only_own_notifications(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/notifications/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 2)
        self.assertEqual(response.data['unread_count'], 1)
        titles = [item['title'] for item in response.data['results']]
        self.assertNotIn('Ajena', titles)

    def test_list_filters_unread(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/notifications/', {'unread': 'true'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Mía')

    def test_unread_count(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/notifications/unread-count/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 1)

    def test_mark_read(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(f'/api/v1/notifications/{self.mine.id}/read/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.mine.refresh_from_db()
        self.assertTrue(self.mine.is_read)

    def test_cannot_mark_other_users_notification(self):
        other_notification = Notification.objects.get(user=self.other)

        self.client.force_authenticate(user=self.user)
        response = self.client.post(
            f'/api/v1/notifications/{other_notification.id}/read/'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        other_notification.refresh_from_db()
        self.assertFalse(other_notification.is_read)

    def test_mark_all_read(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post('/api/v1/notifications/read-all/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['updated'], 1)
        self.assertFalse(
            Notification.objects.filter(user=self.user, is_read=False).exists()
        )

    def test_delete_notification(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            f'/api/v1/notifications/{self.mine.id}/delete/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            Notification.objects.filter(id=self.mine.id).exists()
        )

    def test_cannot_delete_other_users_notification(self):
        other_notification = Notification.objects.get(user=self.other)

        self.client.force_authenticate(user=self.user)
        response = self.client.delete(
            f'/api/v1/notifications/{other_notification.id}/delete/'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(
            Notification.objects.filter(id=other_notification.id).exists()
        )

    def test_delete_all_notifications(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.delete('/api/v1/notifications/delete-all/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['deleted'], 2)
        self.assertFalse(
            Notification.objects.filter(user=self.user).exists()
        )
        # Las notificaciones de otros usuarios no se ven afectadas.
        self.assertTrue(
            Notification.objects.filter(user=self.other).exists()
        )

    def test_requires_authentication(self):
        response = self.client.get('/api/v1/notifications/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class NotificationCleanupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='cleanup@example.com', name='Cleanup', password='Password123'
        )
        self.other = User.objects.create_user(
            email='cleanup.other@example.com', name='Cleanup Other', password='Password123'
        )

    def _create(self, user, is_read: bool, days_old: int | None = None):
        notification = Notification.objects.create(
            user=user,
            type=Notification.Type.TASK_CREATED,
            title='Notificación a limpiar',
            is_read=is_read,
        )
        if days_old is not None:
            Notification.objects.filter(id=notification.id).update(
                created_at=timezone.now() - timedelta(days=days_old)
            )
        return notification

    def test_cleanup_deletes_only_old_read_notifications(self):
        old_read = self._create(self.user, is_read=True, days_old=5)
        recent_read = self._create(self.user, is_read=True, days_old=1)
        old_unread = self._create(self.user, is_read=False, days_old=10)

        deleted = cleanup_read_notifications(user=self.user, days=3)

        self.assertEqual(deleted, 1)
        self.assertFalse(Notification.objects.filter(id=old_read.id).exists())
        self.assertTrue(Notification.objects.filter(id=recent_read.id).exists())
        self.assertTrue(Notification.objects.filter(id=old_unread.id).exists())

    def test_cleanup_without_user_applies_to_all_users(self):
        mine_old_read = self._create(self.user, is_read=True, days_old=5)
        other_old_read = self._create(self.other, is_read=True, days_old=5)

        deleted = cleanup_read_notifications(days=3)

        self.assertEqual(deleted, 2)
        self.assertFalse(Notification.objects.filter(id=mine_old_read.id).exists())
        self.assertFalse(Notification.objects.filter(id=other_old_read.id).exists())

    def test_cleanup_only_affects_the_given_user(self):
        mine_old_read = self._create(self.user, is_read=True, days_old=5)
        other_old_read = self._create(self.other, is_read=True, days_old=5)

        deleted = cleanup_read_notifications(user=self.user, days=3)

        self.assertEqual(deleted, 1)
        self.assertFalse(Notification.objects.filter(id=mine_old_read.id).exists())
        self.assertTrue(Notification.objects.filter(id=other_old_read.id).exists())

    def test_cleanup_command_deletes_old_read_notifications(self):
        old_read = self._create(self.user, is_read=True, days_old=4)

        call_command('cleanup_notifications', days=3)

        self.assertFalse(Notification.objects.filter(id=old_read.id).exists())


@override_settings(CHANNEL_LAYERS=IN_MEMORY_LAYER)
class NotificationWebsocketTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='ws@example.com', name='WS', password='Password123'
        )
        self.other = User.objects.create_user(
            email='ws.other@example.com', name='WS Other', password='Password123'
        )

    def _communicator(self, user=None, token=None, origin=b'http://localhost:5173'):
        # El navegador siempre envía Origin; `AllowedHostsOriginValidator` la
        # exige para dejar pasar el handshake.
        headers = [(b'origin', origin)] if origin else []
        subprotocols = [SUBPROTOCOL, token] if token else None
        return WebsocketCommunicator(
            application,
            '/ws/notifications/',
            headers=headers,
            subprotocols=subprotocols,
        )

    def _token(self, user):
        return str(AccessToken.for_user(user))

    def test_connection_from_disallowed_origin_is_rejected(self):
        async def scenario():
            communicator = self._communicator(
                token=self._token(self.user),
                origin=b'http://evil.example.com',
            )
            connected, _ = await communicator.connect()
            self.assertFalse(connected)
            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_connection_without_origin_is_rejected(self):
        async def scenario():
            communicator = self._communicator(
                token=self._token(self.user),
                origin=None,
            )
            connected, _ = await communicator.connect()
            self.assertFalse(connected)
            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_connection_without_token_is_rejected(self):
        async def scenario():
            communicator = self._communicator()
            connected, code = await communicator.connect()
            self.assertFalse(connected)
            self.assertEqual(code, 4401)
            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_connection_with_invalid_token_is_rejected(self):
        async def scenario():
            communicator = self._communicator(token='invalido')
            connected, code = await communicator.connect()
            self.assertFalse(connected)
            self.assertEqual(code, 4401)
            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_valid_token_connects_and_receives_unread_count(self):
        async def scenario():
            communicator = self._communicator(token=self._token(self.user))
            connected, subprotocol = await communicator.connect()
            self.assertTrue(connected)
            self.assertEqual(subprotocol, SUBPROTOCOL)

            message = await communicator.receive_json_from()
            self.assertEqual(message['type'], 'unread_count')
            self.assertEqual(message['count'], 0)

            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_user_receives_own_notification(self):
        async def scenario():
            communicator = self._communicator(token=self._token(self.user))
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_json_from()  # unread_count inicial

            await database_sync_to_async(notify)(
                self.user,
                Notification.Type.TASK_ASSIGNED,
                'Te asignaron una tarea',
                'Detalle',
                {'task_id': 1, 'module_id': 1},
            )

            message = await communicator.receive_json_from()
            self.assertEqual(message['type'], 'notification')
            self.assertEqual(
                message['notification']['title'], 'Te asignaron una tarea'
            )
            self.assertEqual(message['unread_count'], 1)

            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_notification_is_not_delivered_to_other_user(self):
        async def scenario():
            communicator = self._communicator(token=self._token(self.user))
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_json_from()

            await database_sync_to_async(notify)(
                self.other,
                Notification.Type.TASK_CREATED,
                'Solo para el otro',
            )

            self.assertTrue(await communicator.receive_nothing(timeout=0.3))

            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_ping_pong(self):
        async def scenario():
            communicator = self._communicator(token=self._token(self.user))
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_json_from()

            await communicator.send_json_to({'type': 'ping'})
            message = await communicator.receive_json_from()
            self.assertEqual(message['type'], 'pong')

            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_assigning_task_notifies_assignee(self):
        async def scenario():
            module = await database_sync_to_async(Module.objects.create)(
                name='Módulo WS', creator=self.other
            )
            await database_sync_to_async(UserModule.objects.create)(
                module=module, user=self.other, rol=UserModule.Roles.OWNER
            )
            await database_sync_to_async(UserModule.objects.create)(
                module=module, user=self.user, rol=UserModule.Roles.MEMBER
            )

            communicator = self._communicator(token=self._token(self.user))
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_json_from()

            await database_sync_to_async(create_task)(
                module.id,
                self.other,
                {'title': 'Nueva', 'assignee': self.user},
            )

            message = await communicator.receive_json_from()
            self.assertEqual(message['type'], 'notification')
            self.assertEqual(message['notification']['type'], 'TASK_ASSIGNED')
            self.assertEqual(
                message['notification']['payload']['module_id'], module.id
            )

            await communicator.disconnect()

        async_to_sync(scenario)()

    def test_completing_task_notifies_module_owner(self):
        async def scenario():
            module = await database_sync_to_async(Module.objects.create)(
                name='Módulo WS 2', creator=self.user
            )
            await database_sync_to_async(UserModule.objects.create)(
                module=module, user=self.user, rol=UserModule.Roles.OWNER
            )
            await database_sync_to_async(UserModule.objects.create)(
                module=module, user=self.other, rol=UserModule.Roles.MEMBER
            )
            task = await database_sync_to_async(Tasks.objects.create)(
                module=module, title='Por completar', assignee=self.other
            )

            communicator = self._communicator(token=self._token(self.user))
            connected, _ = await communicator.connect()
            self.assertTrue(connected)
            await communicator.receive_json_from()

            await database_sync_to_async(update_task)(
                module.id,
                task.id,
                self.other,
                {'state': Tasks.TaskState.COMPLETADA},
            )

            message = await communicator.receive_json_from()
            self.assertEqual(message['type'], 'notification')
            self.assertEqual(message['notification']['type'], 'TASK_COMPLETED')

            await communicator.disconnect()

        async_to_sync(scenario)()


class NotificationEventTests(TestCase):
    """
    Comprueba que las acciones de negocio generan las notificaciones correctas.

    Al ejecutarse dentro de la transacción del test, `transaction.on_commit`
    no dispara el push por WebSocket; solo se valida la persistencia.
    """

    def setUp(self):
        self.owner = User.objects.create_user(
            email='events.owner@example.com', name='Owner', password='Password123'
        )
        self.member = User.objects.create_user(
            email='events.member@example.com', name='Member', password='Password123'
        )
        self.other = User.objects.create_user(
            email='events.other@example.com', name='Other', password='Password123'
        )
        self.module = Module.objects.create(name='Módulo Eventos', creator=self.owner)
        UserModule.objects.create(
            module=self.module, user=self.owner, rol=UserModule.Roles.OWNER
        )
        UserModule.objects.create(
            module=self.module, user=self.member, rol=UserModule.Roles.MEMBER
        )
        UserModule.objects.create(
            module=self.module, user=self.other, rol=UserModule.Roles.MEMBER
        )

    def types_for(self, user):
        return list(
            Notification.objects.filter(user=user).values_list('type', flat=True)
        )

    def test_create_task_notifies_assignee_and_other_members(self):
        create_task(
            self.module.id,
            self.owner,
            {'title': 'Nueva', 'assignee': self.member},
        )

        self.assertEqual(self.types_for(self.member), [Notification.Type.TASK_ASSIGNED])
        self.assertEqual(self.types_for(self.other), [Notification.Type.TASK_CREATED])
        self.assertEqual(self.types_for(self.owner), [])

    def test_self_assignment_does_not_notify_assignee(self):
        create_task(
            self.module.id,
            self.member,
            {'title': 'Propia', 'assignee': self.member},
        )

        self.assertEqual(self.types_for(self.member), [])
        self.assertEqual(self.types_for(self.other), [Notification.Type.TASK_CREATED])
        self.assertEqual(self.types_for(self.owner), [Notification.Type.TASK_CREATED])

    def test_reassignment_notifies_new_and_previous_assignee(self):
        task = create_task(
            self.module.id,
            self.owner,
            {'title': 'Reasignable', 'assignee': self.member},
        )
        Notification.objects.all().delete()

        update_task(self.module.id, task.id, self.owner, {'assignee': self.other})

        self.assertEqual(self.types_for(self.other), [Notification.Type.TASK_ASSIGNED])
        self.assertEqual(self.types_for(self.member), [Notification.Type.TASK_UNASSIGNED])
        self.assertEqual(self.types_for(self.owner), [])

    def test_completing_task_notifies_owner_only(self):
        task = create_task(
            self.module.id,
            self.owner,
            {'title': 'Completable', 'assignee': self.member},
        )
        Notification.objects.all().delete()

        update_task(
            self.module.id,
            task.id,
            self.member,
            {'state': Tasks.TaskState.COMPLETADA},
        )

        self.assertEqual(self.types_for(self.owner), [Notification.Type.TASK_COMPLETED])
        self.assertEqual(self.types_for(self.member), [])
        self.assertEqual(self.types_for(self.other), [])

    def test_delete_task_notifies_members_except_actor(self):
        task = create_task(self.module.id, self.owner, {'title': 'Eliminable'})
        Notification.objects.all().delete()

        delete_task(self.module.id, task.id, self.owner)

        self.assertEqual(self.types_for(self.member), [Notification.Type.TASK_DELETED])
        self.assertEqual(self.types_for(self.other), [Notification.Type.TASK_DELETED])
        self.assertEqual(self.types_for(self.owner), [])

    def test_add_member_notifies_added_user(self):
        newcomer = User.objects.create_user(
            email='events.new@example.com', name='New', password='Password123'
        )

        add_member_to_module(self.module.id, newcomer)

        self.assertEqual(self.types_for(newcomer), [Notification.Type.MEMBER_ADDED])

    def test_remove_member_notifies_removed_user(self):
        delete_member_from_module(self.module.id, self.member.id)

        self.assertEqual(
            self.types_for(self.member), [Notification.Type.MEMBER_REMOVED]
        )

    def test_transfer_owner_notifies_new_owner(self):
        edit_rol_member_from_module(self.module.id, self.member.id, self.owner.id)

        self.assertEqual(
            self.types_for(self.member), [Notification.Type.OWNER_TRANSFERRED]
        )

    def test_create_module_notifies_added_members(self):
        create_module(
            self.owner,
            {'name': 'Módulo nuevo', 'description': '', 'members': [self.other]},
        )

        self.assertEqual(self.types_for(self.other), [Notification.Type.MEMBER_ADDED])
        self.assertEqual(self.types_for(self.owner), [])
