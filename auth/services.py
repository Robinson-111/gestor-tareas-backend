from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from account.models import User


def generate_tokens_for_user(user: User) -> dict:
    """
    Genera tokens JWT (access y refresh) con claims personalizados para el usuario.
    """
    refresh = RefreshToken.for_user(user)
    refresh['name'] = user.name
    refresh['email'] = user.email
    refresh['rol'] = user.rol

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'rol': user.rol,
        }
    }


def authenticate_user(email: str, password: str) -> User:
    """
    Autentica al usuario mediante email y contraseña.
    Lanza ValidationError si las credenciales son inválidas.
    """
    user = authenticate(username=email, password=password)
    if not user:
        raise serializers.ValidationError({
            "non_field_errors": ["Correo o contraseña incorrectos."]
        })
    return user


def login_user(email: str, password: str) -> dict:
    """
    Orquesta el login: autentica al usuario y genera el payload con tokens.
    """
    user = authenticate_user(email, password)
    return generate_tokens_for_user(user)


def blacklist_refresh_token(refresh_token_str: str) -> None:
    """
    Invalida (blacklist) un refresh token JWT.
    """
    try:
        token = RefreshToken(refresh_token_str)
        token.blacklist()
    except TokenError:
        raise serializers.ValidationError({
            'refresh': 'El token es inválido o ha expirado.'
        })


def register_user(validated_data: dict) -> User:
    """
    Crea un nuevo usuario con rol USER en el sistema.
    Punto centralizado para agregar lógica colateral (enviar email de bienvenida, etc.).
    """
    data = validated_data.copy()
    data.pop('confirm_password', None)

    user = User.objects.create_user(
        email=data['email'],
        name=data['name'],
        password=data['password'],
        rol=User.Roles.USER
    )
    return user
