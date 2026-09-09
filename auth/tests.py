from rest_framework.test import APITestCase
from rest_framework import status
from account.models import User
class RegisterTests(APITestCase):
    def setUp(self):
        self.register_url = "/auth/register/"  # Ajusta según tu url en auth/urls.py
        self.valid_payload = {
            "name": "Test User",
            "email": "test@example.com",
            "password": "Password123*",
            "confirm_password": "Password123*"
        }
    def test_register_success(self):
        response = self.client.post(self.register_url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(email="test@example.com").exists())
    def test_invalid_email_format(self):
        payload = self.valid_payload.copy()
        payload["email"] = "invalido"
        response = self.client.post(self.register_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Por favor, ingrese un correo electrónico valido", response.data["email"])
    def test_duplicate_email(self):
        User.objects.create_user(email="test@example.com", name="Existing", password="Password123*")
        response = self.client.post(self.register_url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Ya existe un usuario con este email", str(response.data))
    def test_password_mismatch(self):
        payload = self.valid_payload.copy()
        payload["confirm_password"] = "OtraPassword123*"
        response = self.client.post(self.register_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Las contraseñas no coinciden.", response.data["confirm_password"])
    def test_password_min_length(self):
        payload = self.valid_payload.copy()
        payload["password"] = "12345"
        payload["confirm_password"] = "12345"
        response = self.client.post(self.register_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)