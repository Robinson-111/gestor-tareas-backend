from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers.register import RegisterSerializer
from .serializers.login import LoginSerializer
from .serializers.logout import LogoutSerializer
from .serializers.password_reset import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
)
from .services import (
    login_user,
    blacklist_refresh_token,
    register_user,
    request_password_reset,
    confirm_password_reset,
)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        register_user(serializer.validated_data)
        return Response({
            "message": "Usuario registrado exitosamente."
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        tokens_data = login_user(
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password']
        )
        return Response({
            "message": "Usuario autenticado exitosamente.",
            **tokens_data
        }, status=status.HTTP_200_OK)


class PasswordResetRequestView(APIView):
    """Envía el correo con el enlace de recuperación (si el usuario existe)."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        request_password_reset(serializer.validated_data['email'])
        # Respuesta genérica: no revela si el correo está registrado.
        return Response({
            "message": "Si el correo está registrado, recibirás un enlace para "
                       "restablecer tu contraseña."
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """Cambia la contraseña usando el enlace de recuperación."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'password_reset'

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        confirm_password_reset(
            uidb64=serializer.validated_data['uidb64'],
            token=serializer.validated_data['token'],
            new_password=serializer.validated_data['new_password'],
        )
        return Response({
            "message": "Contraseña actualizada exitosamente."
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        blacklist_refresh_token(serializer.validated_data['refresh'])
        return Response({
            "message": "Sesión cerrada exitosamente."
        }, status=status.HTTP_200_OK)


class RefreshTokenView(TokenRefreshView):
    """
    Endpoint para renovar el access token (y rotar refresh token si está configurado).
    """
    permission_classes = [AllowAny]
