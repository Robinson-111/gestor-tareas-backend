"""
Handler global de excepciones de la API.

Contrato único de error:

    {
        "message": "Texto legible para el usuario",
        "errors": {"campo": ["mensaje", ...]},   # opcional
        "code": "codigo_estable"                 # opcional
    }

El status HTTP no cambia: solo se normaliza el cuerpo de la respuesta.
"""

from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler

GENERIC_VALIDATION_MESSAGE = "Revisa los campos del formulario."
GENERIC_ERROR_MESSAGE = "Ha ocurrido un error."

# Claves que DRF/SimpleJWT usan para metadatos y que no son campos de formulario.
RESERVED_KEYS = {"detail", "code", "messages", "non_field_errors"}


def _as_list(value):
    """Normaliza cualquier detalle de DRF a una lista de strings."""
    if isinstance(value, (list, tuple)):
        return [str(item) for item in value]
    return [str(value)]


def _normalize(data):
    """
    Convierte el `data` de una respuesta de error de DRF en (message, errors).

    Casos soportados:
    - str: el propio mensaje.
    - list: primer mensaje + `non_field_errors`.
    - dict: `detail`/`non_field_errors` como mensaje y el resto como campos.
    """
    if isinstance(data, str):
        return data, None

    if isinstance(data, (list, tuple)):
        messages = _as_list(data)
        message = messages[0] if messages else GENERIC_ERROR_MESSAGE
        return message, {"non_field_errors": messages}

    if isinstance(data, dict):
        message = None

        non_field = data.get("non_field_errors")
        if non_field:
            message = _as_list(non_field)[0]

        detail = data.get("detail")
        if isinstance(detail, str):
            message = detail
        elif detail is not None and message is None:
            message = str(detail)

        errors = {
            field: _as_list(value)
            for field, value in data.items()
            if field not in RESERVED_KEYS
        }

        if message is None:
            message = GENERIC_VALIDATION_MESSAGE if errors else GENERIC_ERROR_MESSAGE

        return message, (errors or None)

    return GENERIC_ERROR_MESSAGE, None


def api_exception_handler(exc, context):
    """EXCEPTION_HANDLER global de DRF."""
    response = exception_handler(exc, context)

    # Excepción no controlada (500): se deja que Django la procese.
    if response is None:
        return None

    if isinstance(exc, Throttled) and exc.wait:
        message = f"Demasiados intentos. Inténtalo de nuevo en {int(exc.wait)} segundos."
        errors = None
    else:
        message, errors = _normalize(response.data)

    payload = {"message": message}
    if errors:
        payload["errors"] = errors
    if isinstance(response.data, dict) and response.data.get("code"):
        payload["code"] = str(response.data["code"])

    # Se muta la respuesta existente para conservar headers (Retry-After,
    # WWW-Authenticate, etc.) y el status original.
    response.data = payload
    return response
