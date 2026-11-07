from django.test import SimpleTestCase
from rest_framework.exceptions import (
    AuthenticationFailed,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.test import APITestCase
from rest_framework_simplejwt.exceptions import InvalidToken

from core.exceptions import api_exception_handler


class ApiExceptionHandlerTests(SimpleTestCase):
    """Verifica el contrato {"message", "errors", "code"} del handler global."""

    def handle(self, exc):
        return api_exception_handler(exc, context={})

    def test_string_detail_becomes_message(self):
        response = self.handle(PermissionDenied("No perteneces a este módulo."))

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.data, {"message": "No perteneces a este módulo."})

    def test_field_errors_are_nested_under_errors(self):
        response = self.handle(
            ValidationError({"email": ["Ya existe un usuario con este email"]})
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data["message"], "Revisa los campos del formulario.")
        self.assertEqual(
            response.data["errors"],
            {"email": ["Ya existe un usuario con este email"]},
        )

    def test_non_field_errors_become_message(self):
        response = self.handle(
            ValidationError({"non_field_errors": ["Correo o contraseña incorrectos."]})
        )

        self.assertEqual(
            response.data,
            {"message": "Correo o contraseña incorrectos."},
        )

    def test_validation_error_list_becomes_non_field_errors(self):
        response = self.handle(ValidationError(["Las contraseñas no coinciden."]))

        self.assertEqual(response.data["message"], "Las contraseñas no coinciden.")
        self.assertEqual(
            response.data["errors"],
            {"non_field_errors": ["Las contraseñas no coinciden."]},
        )

    def test_authentication_failed(self):
        response = self.handle(AuthenticationFailed("Credenciales inválidas."))

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data, {"message": "Credenciales inválidas."})

    def test_not_found(self):
        response = self.handle(NotFound("El módulo no existe."))

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data, {"message": "El módulo no existe."})

    def test_throttled_uses_spanish_message_and_keeps_headers(self):
        response = self.handle(Throttled(wait=42))

        self.assertEqual(response.status_code, 429)
        self.assertEqual(
            response.data["message"],
            "Demasiados intentos. Inténtalo de nuevo en 42 segundos.",
        )
        self.assertEqual(response["Retry-After"], "42")

    def test_jwt_code_is_preserved_and_messages_is_dropped(self):
        response = self.handle(InvalidToken())

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data["code"], "token_not_valid")
        self.assertTrue(response.data["message"])
        self.assertNotIn("messages", response.data)


class ErrorEnvelopeIntegrationTests(APITestCase):
    """Comprueba que settings.REST_FRAMEWORK usa el handler personalizado."""

    def test_missing_token_returns_envelope(self):
        response = self.client.get("/api/v1/users/")

        self.assertEqual(response.status_code, 401)
        self.assertIn("message", response.data)
        self.assertNotIn("detail", response.data)
