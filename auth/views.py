from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers
from rest_framework_simplejwt.views import TokenRefreshView
from .serializers.register import RegisterSerializer
from .serializers.login import LoginSerializer
from .serializers.logout import LogoutSerializer
from .services import login_user, blacklist_refresh_token, register_user

class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            register_user(serializer.validated_data)
            return Response({
                "message": "Usuario registrado exitosamente."
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            tokens_data = login_user(
                email=serializer.validated_data['email'],
                password=serializer.validated_data['password']
            )
            return Response({
                "message": "Usuario autenticado exitosamente.",
                **tokens_data
            }, status=status.HTTP_200_OK)
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            blacklist_refresh_token(serializer.validated_data['refresh'])
            return Response({
                "message": "Sesión cerrada exitosamente."
            }, status=status.HTTP_200_OK)
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

class RefreshTokenView(TokenRefreshView):
    """
    Endpoint para renovar el access token (y rotar refresh token si está configurado).
    """
    pass

