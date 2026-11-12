from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
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


def blacklist_all_user_tokens(user: User) -> int:
    """
    Blacklistea todos los refresh tokens emitidos para el usuario.
    Devuelve la cantidad de tokens nuevos agregados a la lista negra.
    """
    count = 0
    for outstanding in OutstandingToken.objects.filter(user=user):
        _, created = BlacklistedToken.objects.get_or_create(token=outstanding)
        if created:
            count += 1
    return count


def request_password_reset(email: str) -> None:
    """
    Envía un correo con el enlace de recuperación.

    Si el correo no pertenece a un usuario activo, no hace nada: la vista
    responde igual para no revelar qué correos existen.
    """
    email = (email or '').strip().lower()
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user is None:
        return

    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    reset_link = (
        f"{settings.FRONTEND_URL}/reset-password"
        f"?uidb64={uidb64}&token={token}"
    )
    expire_minutes = max(settings.PASSWORD_RESET_TIMEOUT // 60, 1)

    send_mail(
        subject='Restablece tu contraseña · TaskFlow',
        message=(
            f"Hola {user.name},\n\n"
            "Recibimos una solicitud para restablecer la contraseña de tu cuenta "
            "de TaskFlow.\n\n"
            f"Enlace de restablecimiento (expira en {expire_minutes} minutos):\n"
            f"{reset_link}\n\n"
            "Si no solicitaste el cambio, ignora este mensaje y tu contraseña "
            "seguirá funcionando.\n\n"
            "Equipo TaskFlow"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=(
            f"<p>Hola <strong>{user.name}</strong>,</p>"
            "<p>Recibimos una solicitud para restablecer la contraseña de tu "
            "cuenta de TaskFlow.</p>"
            f"<p><a href=\"{reset_link}\">Restablecer mi contraseña</a><br>"
            f"<span style=\"font-size:12px;color:#64748B\">El enlace expira en "
            f"{expire_minutes} minutos.</span></p>"
            "<p style=\"font-size:12px;color:#64748B\">Si no solicitaste el "
            "cambio, ignora este mensaje y tu contraseña seguirá "
            "funcionando.</p>"
        ),
    )


def confirm_password_reset(uidb64: str, token: str, new_password: str) -> User:
    """
    Valida el enlace de recuperación y cambia la contraseña del usuario.
    Invalida además todos los refresh tokens activos del usuario.
    """
    generic_error = serializers.ValidationError({
        'non_field_errors': ['El enlace es inválido o ha expirado.'],
    })

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        raise generic_error

    if not user.is_active or not default_token_generator.check_token(user, token):
        raise generic_error

    try:
        validate_password(new_password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({'new_password': list(exc.messages)})

    user.set_password(new_password)
    user.save(update_fields=['password'])

    # Cambiar la contraseña invalida el token usado; las sesiones activas
    # también se cierran para que solo el nuevo acceso sea válido.
    blacklist_all_user_tokens(user)
    return user
