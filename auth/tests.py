from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.cache import cache
from django.test import override_settings
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from account.models import User


class RegisterTests(APITestCase):
    def setUp(self):
        self.register_url = "/api/v1/auth/register/"  # Ajusta según tu url en auth/urls.py
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
        self.assertIn("Por favor, ingrese un correo electrónico valido", response.data["errors"]["email"])

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
        self.assertIn("Las contraseñas no coinciden.", response.data["errors"]["confirm_password"])

    def test_password_min_length(self):
        payload = self.valid_payload.copy()
        payload["password"] = "12345"
        payload["confirm_password"] = "12345"
        response = self.client.post(self.register_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_register_with_admin_role(self):
        """Intento de registro público como ADMIN debe responder 400 Bad Request"""
        payload = self.valid_payload.copy()
        payload["rol"] = "ADMIN"
        response = self.client.post(self.register_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("rol", response.data["errors"])

    def test_cannot_register_with_super_admin_role(self):
        """Intento de registro público como SUPER_ADMIN debe responder 400 Bad Request"""
        payload = self.valid_payload.copy()
        payload["rol"] = "SUPER_ADMIN"
        response = self.client.post(self.register_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("rol", response.data["errors"])

    def test_registered_user_has_regular_user_role(self):
        """Cualquier usuario registrado por este endpoint debe tener rol USER"""
        response = self.client.post(self.register_url, self.valid_payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_user = User.objects.get(email=self.valid_payload["email"])
        self.assertEqual(created_user.rol, User.Roles.USER)


class LoginTests(APITestCase):
    def setUp(self):
        cache.clear()  # Evita que el throttle de login afecte entre tests
        self.login_url = "/api/v1/auth/login/"
        self.email = "test@example.com"
        self.password = "Password123*"
        # Creamos un usuario de prueba para autenticarnos
        self.user = User.objects.create_user(
            email=self.email,
            name="Test User",
            password=self.password
        )

    def test_login_success(self):
        payload = {
            "email": self.email,
            "password": self.password
        }
        response = self.client.post(self.login_url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("message"), "Usuario autenticado exitosamente.")

    def test_login_wrong_password(self):
        payload = {
            "email": self.email,
            "password": "PasswordIncorrecta123*"
        }
        response = self.client.post(self.login_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Correo o contraseña incorrectos.", str(response.data))

    def test_login_user_not_found(self):
        payload = {
            "email": "noexiste@example.com",
            "password": self.password
        }
        response = self.client.post(self.login_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Correo o contraseña incorrectos.", str(response.data))

    def test_login_invalid_email_format(self):
        payload = {
            "email": "correo_invalido",
            "password": self.password
        }
        response = self.client.post(self.login_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Por favor, ingrese un correo electrónico válido.", response.data["errors"]["email"])

    def test_login_blank_fields(self):
        payload = {
            "email": "",
            "password": ""
        }
        response = self.client.post(self.login_url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("El correo electrónico no puede estar vacío.", response.data["errors"]["email"])
        self.assertIn("La contraseña no puede estar vacía.", response.data["errors"]["password"])


class LogoutTests(APITestCase):
    def setUp(self):
        self.logout_url = "/api/v1/auth/logout/"
        self.refresh_url = "/api/v1/auth/refresh/"
        self.user = User.objects.create_user(
            email="logout_user@example.com",
            name="Logout User",
            password="Password123*"
        )
        self.refresh_token = str(RefreshToken.for_user(self.user))
        self.client.force_authenticate(user=self.user)

    def test_logout_unauthenticated_fails(self):
        """Sin access token no se puede cerrar sesión (401 Unauthorized)"""
        self.client.force_authenticate(user=None)
        response = self.client.post(self.logout_url, {"refresh": self.refresh_token})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_success(self):
        response = self.client.post(self.logout_url, {"refresh": self.refresh_token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("message"), "Sesión cerrada exitosamente.")

    def test_logout_blacklists_token(self):
        # Primero cerramos sesión
        logout_response = self.client.post(self.logout_url, {"refresh": self.refresh_token})
        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)

        # Intentar refrescar con el token en lista negra debe fallar
        refresh_response = self.client.post(self.refresh_url, {"refresh": self.refresh_token})
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_already_blacklisted_token(self):
        # Blacklist primeramente
        self.client.post(self.logout_url, {"refresh": self.refresh_token})
        # Intentar hacer logout de nuevo con el mismo token
        response = self.client.post(self.logout_url, {"refresh": self.refresh_token})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("El token es inválido o ha expirado.", str(response.data))

    def test_logout_invalid_token(self):
        response = self.client.post(self.logout_url, {"refresh": "token_invalido_123"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("El token es inválido o ha expirado.", str(response.data))

    def test_logout_missing_token(self):
        response = self.client.post(self.logout_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("El token de actualización (refresh) es obligatorio.", response.data["errors"]["refresh"])

    def test_logout_blank_token(self):
        response = self.client.post(self.logout_url, {"refresh": ""})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("El token de actualización no puede estar vacío.", response.data["errors"]["refresh"])


class RefreshTokenTests(APITestCase):
    def setUp(self):
        self.refresh_url = "/api/v1/auth/refresh/"
        self.user = User.objects.create_user(
            email="refresh_user@example.com",
            name="Refresh User",
            password="Password123*"
        )
        self.refresh_token = str(RefreshToken.for_user(self.user))

    def test_refresh_token_success(self):
        response = self.client.post(self.refresh_url, {"refresh": self.refresh_token})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_refresh_token_invalid(self):
        response = self.client.post(self.refresh_url, {"refresh": "token_falso"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_missing(self):
        response = self.client.post(self.refresh_url, {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class AuthSecurityTests(APITestCase):
    """Pruebas de endurecimiento: privacidad por defecto, contraseñas y throttling."""

    def setUp(self):
        cache.clear()

    def register(self, password, email='nuevo@example.com', name='Usuario Nuevo'):
        return self.client.post(
            '/api/v1/auth/register/',
            {
                'name': name,
                'email': email,
                'password': password,
                'confirm_password': password,
            }
        )

    def test_short_password_is_rejected(self):
        response = self.register('Ab1')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data["errors"])

    def test_numeric_password_is_rejected(self):
        response = self.register('12345678')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data["errors"])

    def test_common_password_is_rejected(self):
        response = self.register('password')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data["errors"])

    def test_password_similar_to_name_is_rejected(self):
        response = self.register('Robinson2026', email='robinson@example.com', name='Robinson')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', response.data["errors"])

    def test_strong_password_is_accepted(self):
        response = self.register('Xk9#mQ2vLp7z', email='fuerte@example.com')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_protected_endpoints_require_authentication(self):
        for url in ('/api/v1/modules/', '/api/v1/users/'):
            response = self.client.get(url)
            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
                msg=f'{url} debería exigir autenticación'
            )

    def test_login_is_throttled(self):
        payload = {'email': 'nadie@example.com', 'password': 'Cualquiera123'}

        for _ in range(10):
            response = self.client.post('/api/v1/auth/login/', payload)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.post('/api/v1/auth/login/', payload)
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)


@override_settings(MAILERS={'default': {'BACKEND': 'django.core.mail.backends.locmem.EmailBackend'}})
class PasswordResetTests(APITestCase):
    """Recuperación de contraseña: solicitud por correo y confirmación con token."""

    request_url = '/api/v1/auth/password-reset/'
    confirm_url = '/api/v1/auth/password-reset/confirm/'

    def setUp(self):
        cache.clear()

    def make_user(self, email='reset@example.com', password='Password123*', name='Ana Torres'):
        return User.objects.create_user(email=email, name=name, password=password)

    @staticmethod
    def build_link(user):
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        return uidb64, token

    # ------------------------------------------------------------------
    # Solicitud del enlace
    # ------------------------------------------------------------------

    def test_request_sends_email_to_existing_user(self):
        user = self.make_user()

        response = self.client.post(self.request_url, {'email': 'RESET@example.com'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [user.email])
        body = mail.outbox[0].body
        self.assertIn('/reset-password?uidb64=', body)
        self.assertIn('token=', body)

    def test_request_unknown_email_is_generic_and_silent(self):
        response = self.client.post(self.request_url, {'email': 'nadie@example.com'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_request_response_does_not_reveal_account(self):
        self.make_user()

        existing = self.client.post(self.request_url, {'email': 'reset@example.com'})
        unknown = self.client.post(self.request_url, {'email': 'nadie@example.com'})

        self.assertEqual(existing.data['message'], unknown.data['message'])

    def test_request_inactive_user_gets_no_email(self):
        user = self.make_user(email='inactivo@example.com')
        user.is_active = False
        user.save()

        response = self.client.post(self.request_url, {'email': 'inactivo@example.com'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_request_missing_email_is_rejected(self):
        response = self.client.post(self.request_url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data['errors'])

    def test_request_invalid_email_is_rejected(self):
        response = self.client.post(self.request_url, {'email': 'no-es-correo'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data['errors'])

    # ------------------------------------------------------------------
    # Confirmación del restablecimiento
    # ------------------------------------------------------------------

    def test_confirm_with_valid_token_changes_password(self):
        user = self.make_user()
        uidb64, token = self.build_link(user)

        response = self.client.post(self.confirm_url, {
            'uidb64': uidb64,
            'token': token,
            'new_password': 'NewPassword123*',
            'confirm_password': 'NewPassword123*',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.check_password('NewPassword123*'))

    def test_confirm_allows_login_with_new_password(self):
        user = self.make_user()
        uidb64, token = self.build_link(user)
        self.client.post(self.confirm_url, {
            'uidb64': uidb64,
            'token': token,
            'new_password': 'NewPassword123*',
            'confirm_password': 'NewPassword123*',
        })

        response = self.client.post('/api/v1/auth/login/', {
            'email': user.email,
            'password': 'NewPassword123*',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_confirm_blacklists_existing_refresh_tokens(self):
        user = self.make_user()
        old_refresh_str = str(RefreshToken.for_user(user))
        uidb64, token = self.build_link(user)

        response = self.client.post(self.confirm_url, {
            'uidb64': uidb64,
            'token': token,
            'new_password': 'NewPassword123*',
            'confirm_password': 'NewPassword123*',
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        with self.assertRaises(TokenError):
            RefreshToken(old_refresh_str).check_blacklist()

    def test_confirm_invalid_token_is_rejected(self):
        user = self.make_user()
        uidb64, _ = self.build_link(user)

        response = self.client.post(self.confirm_url, {
            'uidb64': uidb64,
            'token': 'token-falso',
            'new_password': 'NewPassword123*',
            'confirm_password': 'NewPassword123*',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        user.refresh_from_db()
        self.assertTrue(user.check_password('Password123*'))

    def test_confirm_invalid_uid_is_rejected(self):
        response = self.client.post(self.confirm_url, {
            'uidb64': 'zzzz',
            'token': 'cualquiera',
            'new_password': 'NewPassword123*',
            'confirm_password': 'NewPassword123*',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_confirm_password_mismatch_is_rejected(self):
        user = self.make_user()
        uidb64, token = self.build_link(user)

        response = self.client.post(self.confirm_url, {
            'uidb64': uidb64,
            'token': token,
            'new_password': 'NewPassword123*',
            'confirm_password': 'Otra45678*',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('confirm_password', response.data['errors'])
        user.refresh_from_db()
        self.assertTrue(user.check_password('Password123*'))

    def test_confirm_weak_password_is_rejected(self):
        user = self.make_user()
        uidb64, token = self.build_link(user)

        response = self.client.post(self.confirm_url, {
            'uidb64': uidb64,
            'token': token,
            'new_password': '12345678',
            'confirm_password': '12345678',
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('new_password', response.data['errors'])
        user.refresh_from_db()
        self.assertTrue(user.check_password('Password123*'))

    def test_confirm_token_is_single_use(self):
        user = self.make_user()
        uidb64, token = self.build_link(user)
        payload = {
            'uidb64': uidb64,
            'token': token,
            'new_password': 'NewPassword123*',
            'confirm_password': 'NewPassword123*',
        }

        first = self.client.post(self.confirm_url, payload)
        second = self.client.post(self.confirm_url, payload)

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
