from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from account.models import User
from modules.models import Module, UserModule
from tasks.models import Tasks


class TaskEndpointsTestBase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com', name='Owner', password='Password123'
        )
        self.member = User.objects.create_user(
            email='member@example.com', name='Member', password='Password123'
        )
        self.other = User.objects.create_user(
            email='other@example.com', name='Other', password='Password123'
        )
        self.outsider = User.objects.create_user(
            email='outsider@example.com', name='Outsider', password='Password123'
        )

        self.module = Module.objects.create(name='Módulo de prueba', creator=self.owner)
        UserModule.objects.create(
            module=self.module, user=self.owner, rol=UserModule.Roles.OWNER
        )
        UserModule.objects.create(
            module=self.module, user=self.member, rol=UserModule.Roles.MEMBER
        )
        UserModule.objects.create(
            module=self.module, user=self.other, rol=UserModule.Roles.MEMBER
        )

    def list_url(self):
        return reverse('module_tasks', kwargs={'id': self.module.id})

    def detail_url(self, task):
        return reverse(
            'module_task_detail',
            kwargs={'id': self.module.id, 'task_id': task.id}
        )


class TaskListCreateTests(TaskEndpointsTestBase):
    def test_non_member_cannot_list_tasks(self):
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(self.list_url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_existent_module_returns_404(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(
            reverse('module_tasks', kwargs={'id': 9999})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_task_with_default_priority(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            self.list_url(), {'title': 'Tarea sin prioridad'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['priority'], Tasks.TaskPriority.MEDIA)
        self.assertEqual(response.data['data']['state'], Tasks.TaskState.PENDIENTE)
        self.assertIsNone(response.data['data']['assignee_id'])

    def test_create_task_with_assignee(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            self.list_url(),
            {'title': 'Tarea asignada', 'assignee_id': self.other.id},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['data']['assignee_id'], self.other.id)

    def test_cannot_assign_task_to_non_member(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            self.list_url(),
            {'title': 'Tarea inválida', 'assignee_id': self.outsider.id},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('assignee_id', response.data)

    def test_rejects_unknown_fields_on_create(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            self.list_url(),
            {'title': 'Tarea', 'module_id': self.module.id},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('module_id', response.data)

    def test_list_filters_by_state_and_search(self):
        Tasks.objects.create(module=self.module, title='Implementar JWT')
        Tasks.objects.create(
            module=self.module,
            title='Documentar API',
            state=Tasks.TaskState.COMPLETADA
        )

        self.client.force_authenticate(user=self.member)

        response = self.client.get(self.list_url(), {'estado': 'COMPLETADA'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Documentar API')

        response = self.client.get(self.list_url(), {'search': 'jwt'})
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Implementar JWT')

    def test_list_rejects_invalid_state(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.get(self.list_url(), {'estado': 'CANCELADA'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TaskDetailTests(TaskEndpointsTestBase):
    def test_member_cannot_update_task_assigned_to_another(self):
        task = Tasks.objects.create(
            module=self.module, title='Tarea', assignee=self.other
        )

        self.client.force_authenticate(user=self.member)
        response = self.client.patch(
            self.detail_url(task), {'state': 'COMPLETADA'}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_can_update_own_task(self):
        task = Tasks.objects.create(
            module=self.module, title='Tarea', assignee=self.member
        )

        self.client.force_authenticate(user=self.member)
        response = self.client.patch(
            self.detail_url(task),
            {'state': 'EN_CURSO', 'priority': 'ALTA'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['state'], 'EN_CURSO')
        self.assertEqual(response.data['data']['priority'], 'ALTA')

    def test_member_can_take_unassigned_task(self):
        task = Tasks.objects.create(module=self.module, title='Sin asignar')

        self.client.force_authenticate(user=self.member)
        response = self.client.patch(
            self.detail_url(task), {'assignee_id': self.member.id}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['assignee_id'], self.member.id)

    def test_member_cannot_assign_unassigned_task_to_another(self):
        task = Tasks.objects.create(module=self.module, title='Sin asignar')

        self.client.force_authenticate(user=self.member)
        response = self.client.patch(
            self.detail_url(task), {'assignee_id': self.other.id}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_can_unassign_own_task(self):
        task = Tasks.objects.create(
            module=self.module, title='Tarea', assignee=self.member
        )

        self.client.force_authenticate(user=self.member)
        response = self.client.patch(
            self.detail_url(task), {'assignee_id': None}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data['data']['assignee_id'])

    def test_owner_can_update_any_task(self):
        task = Tasks.objects.create(
            module=self.module, title='Tarea', assignee=self.other
        )

        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            self.detail_url(task),
            {'assignee_id': self.member.id, 'state': 'COMPLETADA'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['assignee_id'], self.member.id)

    def test_task_from_other_module_returns_404(self):
        other_module = Module.objects.create(name='Otro', creator=self.owner)
        UserModule.objects.create(
            module=other_module, user=self.owner, rol=UserModule.Roles.OWNER
        )
        task = Tasks.objects.create(module=other_module, title='Ajena')

        self.client.force_authenticate(user=self.owner)
        response = self.client.get(
            reverse(
                'module_task_detail',
                kwargs={'id': self.module.id, 'task_id': task.id}
            )
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_permissions(self):
        own_task = Tasks.objects.create(
            module=self.module, title='Propia', assignee=self.member
        )
        unassigned_task = Tasks.objects.create(
            module=self.module, title='Libre'
        )
        other_task = Tasks.objects.create(
            module=self.module, title='Ajena', assignee=self.other
        )

        self.client.force_authenticate(user=self.member)

        response = self.client.delete(self.detail_url(other_task))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client.delete(self.detail_url(own_task))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.delete(self.detail_url(unassigned_task))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_owner_can_delete_any_task(self):
        task = Tasks.objects.create(
            module=self.module, title='Ajena', assignee=self.other
        )

        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(self.detail_url(task))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Tasks.objects.filter(id=task.id).exists())
