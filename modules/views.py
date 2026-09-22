from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from .services import get_modules_list, create_module
from .serializers.modules import ModuleSerializer


class ModuleListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        modules = get_modules_list()
        serializer = ModuleSerializer(modules, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ModuleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        module = create_module(
            creator=request.user,
            validated_data=serializer.validated_data
        )

        response_serializer = ModuleSerializer(module)
        return Response({
            "message": "Módulo creado exitosamente.",
            "data": response_serializer.data
        }, status=status.HTTP_201_CREATED)
