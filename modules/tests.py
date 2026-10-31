from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from account.models import User
from modules.models import Module, UserModule
from tasks.models import Tasks


class ModuleEndpointsTestBase(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='owner@example.com', name='Owner', password='Password123'
        )
        self.member = User.objects.create_user(
            email='member@example.com', name='Member', password='Password123'
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

    def detail_url(self):
        return reverse('module_detail', kwargs={'id': self.module.id})

    def members_url(self):
        return reverse('members_module_list', kwargs={'id': self.module.id})

    def member_detail_url(self, user):
        return reverse(
            'members_module_delete',
            kwargs={'id': self.module.id, 'user_id': user.id}
        )


class ModuleDetailTests(ModuleEndpointsTestBase):
    def test_non_member_cannot_view_module(self):
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(self.detail_url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_can_view_module(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.get(self.detail_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.module.id)

    def test_non_member_cannot_view_members(self):
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(self.members_url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_member_can_view_members(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.get(self.members_url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_non_existent_module_returns_404(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.get(
            reverse('module_detail', kwargs={'id': 9999})
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class ModuleUpdateDeleteTests(ModuleEndpointsTestBase):
    def test_member_cannot_update_module(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.patch(
            self.detail_url(), {'name': 'Hackeado'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.module.refresh_from_db()
        self.assertEqual(self.module.name, 'Módulo de prueba')

    def test_member_cannot_change_module_state(self):
        Tasks.objects.create(
            module=self.module,
            title='Tarea',
            state=Tasks.TaskState.COMPLETADA
        )
        self.client.force_authenticate(user=self.member)
        response = self.client.patch(
            self.detail_url(), {'state': 'COMPLETADO'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_update_module(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            self.detail_url(),
            {'name': 'Nuevo nombre', 'description': 'Nueva descripción'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['name'], 'Nuevo nombre')

    def test_owner_cannot_complete_module_with_pending_tasks(self):
        Tasks.objects.create(module=self.module, title='Pendiente')
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            self.detail_url(), {'state': 'COMPLETADO'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_member_cannot_delete_module(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.delete(self.detail_url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Module.objects.filter(id=self.module.id).exists())

    def test_outsider_cannot_delete_module(self):
        self.client.force_authenticate(user=self.outsider)
        response = self.client.delete(self.detail_url())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Module.objects.filter(id=self.module.id).exists())

    def test_owner_can_delete_module_and_its_tasks(self):
        task = Tasks.objects.create(module=self.module, title='Tarea')

        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(self.detail_url())

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Module.objects.filter(id=self.module.id).exists())
        self.assertFalse(Tasks.objects.filter(id=task.id).exists())


class ModuleListingTests(ModuleEndpointsTestBase):
    def test_list_returns_only_user_modules(self):
        other_module = Module.objects.create(name='Ajeno', creator=self.outsider)
        UserModule.objects.create(
            module=other_module, user=self.outsider, rol=UserModule.Roles.OWNER
        )

        self.client.force_authenticate(user=self.member)
        response = self.client.get(reverse('modules_list'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 1)
        self.assertEqual(response.data['results'][0]['id'], self.module.id)

    def test_list_is_empty_for_user_without_modules(self):
        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(reverse('modules_list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total'], 0)

    def test_list_search_by_name(self):
        Module.objects.create(name='Marketing', creator=self.owner)
        UserModule.objects.create(
            module=Module.objects.get(name='Marketing'),
            user=self.owner,
            rol=UserModule.Roles.MEMBER
        )

        self.client.force_authenticate(user=self.owner)
        response = self.client.get(reverse('modules_list'), {'search': 'market'})

        self.assertEqual(response.data['total'], 1)
        self.assertEqual(response.data['results'][0]['name'], 'Marketing')

    def test_claimable_lists_only_modules_without_owner(self):
        ownerless = Module.objects.create(name='Sin dueño', creator=self.owner)

        self.client.force_authenticate(user=self.outsider)
        response = self.client.get(reverse('modules_claimable'))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        ids = [module['id'] for module in response.data['results']]
        self.assertIn(ownerless.id, ids)
        self.assertNotIn(self.module.id, ids)

    def test_claimable_requires_authentication(self):
        response = self.client.get(reverse('modules_claimable'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class ModuleMembersTests(ModuleEndpointsTestBase):
    def test_member_cannot_add_member(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.post(
            self.members_url(), {'user_id': self.outsider.id}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_adds_member_as_member(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            self.members_url(), {'user_id': self.outsider.id}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        membership = UserModule.objects.get(
            module=self.module, user=self.outsider
        )
        self.assertEqual(membership.rol, UserModule.Roles.MEMBER)

    def test_owner_cannot_add_member_with_owner_role(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            self.members_url(),
            {'user_id': self.outsider.id, 'rol': 'OWNER'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('rol', response.data)
        self.assertFalse(
            UserModule.objects.filter(module=self.module, user=self.outsider).exists()
        )

    def test_cannot_add_duplicate_member(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(
            self.members_url(), {'user_id': self.member.id}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_member_cannot_remove_member(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.delete(self.member_detail_url(self.owner))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_cannot_remove_owner(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(self.member_detail_url(self.owner))
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_owner_removes_member_and_unassigns_tasks(self):
        task = Tasks.objects.create(
            module=self.module, title='Tarea', assignee=self.member
        )

        self.client.force_authenticate(user=self.owner)
        response = self.client.delete(self.member_detail_url(self.member))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            UserModule.objects.filter(module=self.module, user=self.member).exists()
        )
        task.refresh_from_db()
        self.assertIsNone(task.assignee_id)

    def test_member_cannot_transfer_ownership(self):
        self.client.force_authenticate(user=self.member)
        response = self.client.patch(
            self.member_detail_url(self.member), {}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_transfers_ownership(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.patch(
            self.member_detail_url(self.member), {}, format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['rol'], UserModule.Roles.OWNER)
        self.assertEqual(
            UserModule.objects.get(module=self.module, user=self.owner).rol,
            UserModule.Roles.MEMBER
        )


class LeaveModuleTests(ModuleEndpointsTestBase):
    def test_member_can_leave_and_tasks_are_unassigned(self):
        task = Tasks.objects.create(
            module=self.module, title='Tarea', assignee=self.member
        )

        self.client.force_authenticate(user=self.member)
        response = self.client.post(reverse('module_leave', kwargs={'id': self.module.id}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            UserModule.objects.filter(module=self.module, user=self.member).exists()
        )
        task.refresh_from_db()
        self.assertIsNone(task.assignee_id)
        self.assertTrue(Tasks.objects.filter(id=task.id).exists())

    def test_owner_cannot_leave_module(self):
        self.client.force_authenticate(user=self.owner)
        response = self.client.post(reverse('module_leave', kwargs={'id': self.module.id}))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            UserModule.objects.filter(module=self.module, user=self.owner).exists()
        )

    def test_non_member_cannot_leave_module(self):
        self.client.force_authenticate(user=self.outsider)
        response = self.client.post(reverse('module_leave', kwargs={'id': self.module.id}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ClaimModuleTests(ModuleEndpointsTestBase):
    def test_non_member_can_claim_ownerless_module(self):
        ownerless = Module.objects.create(name='Sin dueño', creator=self.owner)

        self.client.force_authenticate(user=self.outsider)
        response = self.client.patch(
            reverse('module_claim_ownership', kwargs={'id': ownerless.id})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        membership = UserModule.objects.get(module=ownerless, user=self.outsider)
        self.assertEqual(membership.rol, UserModule.Roles.OWNER)

    def test_cannot_claim_module_with_owner(self):
        self.client.force_authenticate(user=self.outsider)
        response = self.client.patch(
            reverse('module_claim_ownership', kwargs={'id': self.module.id})
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
