from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from account.models import User
from account.serializers.user import UserSerializer
from account.permissions import IsAdminOrSuperAdmin


class UserListView(APIView):
    permission_classes = [IsAuthenticated] # Validar token

    def get(self, request):
        users = User.objects.all()
        
        #pasar serializer con many=True
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UserDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrSuperAdmin]

    def get(self, request, id):
        user = get_object_or_404(User, id=id)

        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, id):
        user_to_delete = get_object_or_404(User, id=id)
        current_user = request.user

        #Un Admin no puede eliminar otro admin y menos un SuperAdmin
        if current_user.is_admin and user_to_delete.is_admin_or_super:
            return Response(
                {"error": "No tienes permisos para eliminar a este nivel de usuario"},
                status=status.HTTP_403_FORBIDDEN
            )

        #No permitir eliminar el  SuperAdmin
        if user_to_delete.is_super_admin:
            total_super_admin = User.objects.filter(rol= User.Roles.SUPER_ADMIN).count()

            if total_super_admin <= 1:
                return Response(
                    {"error" : "No se puede eliminar el único Super Admin del sistema"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        user_to_delete.delete()

        serializer = UserSerializer(user_to_delete)
        return Response(
            {"message": "Usuario eliminado exitosamente"},
            status=status.HTTP_200_OK
        )