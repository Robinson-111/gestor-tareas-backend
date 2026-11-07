from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers.register import RegisterSerializer
from .serializers.login import LoginSerializer
from .serializers.logout import LogoutSerializer
from .services import login_user, blacklist_refresh_token, register_user


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
