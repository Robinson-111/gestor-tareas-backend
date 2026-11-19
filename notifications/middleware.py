from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken

from account.models import User

SUBPROTOCOL = 'taskflow.jwt'


def extract_token(scope) -> str | None:
    """
    Obtiene el JWT del handshake.

    El navegador no permite cabeceras personalizadas en `WebSocket`, así que
    el cliente envía `Sec-WebSocket-Protocol: taskflow.jwt, <token>`.
    También se admite `Authorization: Bearer <token>` para clientes que sí
    puedan enviar cabeceras (apps nativas, tests, herramientas).
    """
    headers = dict(scope.get('headers') or [])
    authorization = headers.get(b'authorization', b'').decode('latin-1')

    if authorization.lower().startswith('bearer '):
        return authorization[7:].strip()

    subprotocols = scope.get('subprotocols') or []

    if SUBPROTOCOL in subprotocols:
        index = subprotocols.index(SUBPROTOCOL)
        if index + 1 < len(subprotocols):
            return subprotocols[index + 1]

    return None


@database_sync_to_async
def get_user(user_id: int):
    try:
        return User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware:
    """Middleware ASGI que valida el JWT y deja el usuario en el scope."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        subprotocols = scope.get('subprotocols') or []
        scope['user'] = AnonymousUser()
        scope['ws_subprotocol'] = (
            SUBPROTOCOL if SUBPROTOCOL in subprotocols else None
        )

        token = extract_token(scope)

        if token:
            try:
                validated = AccessToken(token)
                scope['user'] = await get_user(validated['user_id'])
            except (TokenError, KeyError):
                scope['user'] = AnonymousUser()

        return await self.inner(scope, receive, send)
