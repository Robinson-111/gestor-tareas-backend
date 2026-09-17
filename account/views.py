from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from account.models import User
from account.serializers.user import UserSerializer


class UserListView(APIView):
    def get(self, request):
        users = User.objects.all()
        
        #pasar serializer con many=True
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class UserDetailView(APIView):
    def get(self, request, id):
        user = get_object_or_404(User, id=id)

        serializer = UserSerializer(user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, id):
        user_to_delete = get_object_or_404(User, id=id)
        user_to_delete.delete()

        serializer = UserSerializer(user_to_delete)
        return Response(
            {"message": "Usuario eliminado exitosamente"},
            status=status.HTTP_200_OK
        )