# account/tests.py
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from account.models import User

class UserEndpointsTests(APITestCase):

    def setUp(self):
        # 1. Crear usuarios de cada rol
        self.super_admin = User.objects.create_superuser(
            email="superadmin@test.com",
            name="Super Admin",
            password="Password123*"
        )
        self.admin = User.objects.create_user(
            email="admin@test.com",
            name="Admin User",
            password="Password123*",
            rol=User.Roles.ADMIN
        )
        self.regular_user = User.objects.create_user(
            email="user@test.com",
            name="Regular User",
            password="Password123*",
            rol=User.Roles.USER
        )

    # ==========================================
    # TESTS: GET /users/ (UserListView)
    # ==========================================
    def test_get_users_unauthenticated_fails(self):
        """Sin token debe responder 401 Unauthorized"""
        url = reverse('users')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_users_authenticated_success(self):
        """Usuario autenticado puede listar usuarios (200 OK)"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('users')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 3)

    # ==========================================
    # TESTS: GET /users/<id>/ (UserDetailView)
    # ==========================================
    def test_get_user_detail_unauthenticated_fails(self):
        """Sin token debe responder 401 Unauthorized"""
        url = reverse('user', kwargs={'id': self.regular_user.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_access_user_detail(self):
        """Un usuario regular no tiene permiso para ver el detalle (403 Forbidden)"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('user', kwargs={'id': self.regular_user.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_get_user_detail_success(self):
        """Un ADMIN puede obtener el detalle de un usuario (200 OK)"""
        self.client.force_authenticate(user=self.admin)
        url = reverse('user', kwargs={'id': self.regular_user.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.regular_user.id)
        self.assertEqual(response.data['email'], self.regular_user.email)
        self.assertEqual(response.data['name'], self.regular_user.name)

    def test_super_admin_can_get_user_detail_success(self):
        """Un SUPER_ADMIN puede obtener el detalle de un usuario (200 OK)"""
        self.client.force_authenticate(user=self.super_admin)
        url = reverse('user', kwargs={'id': self.admin.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.admin.id)
        self.assertEqual(response.data['email'], self.admin.email)

    def test_get_user_detail_not_found(self):
        """Consultar un usuario que no existe debe responder 404 Not Found"""
        self.client.force_authenticate(user=self.admin)
        url = reverse('user', kwargs={'id': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # ==========================================
    # TESTS: DELETE /users/<id>/ (UserDetailView)
    # ==========================================
    def test_delete_user_unauthenticated_fails(self):
        """Sin token no se puede eliminar (401 Unauthorized)"""
        url = reverse('user', kwargs={'id': self.regular_user.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_regular_user_cannot_delete_user(self):
        """Un usuario regular no puede eliminar usuarios (403 Forbidden)"""
        self.client.force_authenticate(user=self.regular_user)
        url = reverse('user', kwargs={'id': self.regular_user.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_delete_super_admin(self):
        """Un ADMIN no puede eliminar un SUPER_ADMIN (403 Forbidden)"""
        self.client.force_authenticate(user=self.admin)
        url = reverse('user', kwargs={'id': self.super_admin.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("No tienes permisos", response.data["error"])

    def test_admin_cannot_delete_another_admin(self):
        """Un ADMIN no puede eliminar a otro ADMIN (403 Forbidden)"""
        other_admin = User.objects.create_user(
            email="admin2@test.com", name="Admin Two", password="Password123*", rol=User.Roles.ADMIN
        )
        self.client.force_authenticate(user=self.admin)
        url = reverse('user', kwargs={'id': other_admin.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("No tienes permisos", response.data["error"])

    def test_admin_can_delete_regular_user(self):
        """Un ADMIN puede eliminar a un usuario regular exitosamente (200 OK)"""
        self.client.force_authenticate(user=self.admin)
        url = reverse('user', kwargs={'id': self.regular_user.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(id=self.regular_user.id).exists())

    def test_cannot_delete_last_super_admin(self):
        """No se puede eliminar si es el único SUPER_ADMIN (400 Bad Request)"""
        self.client.force_authenticate(user=self.super_admin)
        url = reverse('user', kwargs={'id': self.super_admin.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("No se puede eliminar el único Super Admin", response.data["error"])

    def test_super_admin_can_delete_user(self):
        """Un SUPER_ADMIN puede eliminar usuarios exitosamente (200 OK)"""
        self.client.force_authenticate(user=self.super_admin)
        url = reverse('user', kwargs={'id': self.regular_user.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(id=self.regular_user.id).exists())

    def test_delete_user_not_found(self):
        """Intentar eliminar un usuario inexistente responde 404 Not Found"""
        self.client.force_authenticate(user=self.super_admin)
        url = reverse('user', kwargs={'id': 99999})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

