from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.http import Http404

from .services import get_modules_list, create_module, get_module, edit_module, delete_module
from .serializers.modules import ModuleSerializer
from .serializers.module_create import ModuleCreateSerializer


class ModuleListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        modules = get_modules_list()
        serializer = ModuleSerializer(modules, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ModuleCreateSerializer(data=request.data)
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


class ModuleDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        module = get_module(id)
        serializer = ModuleSerializer(module)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, id):
        module = get_module(id)
        serializer = ModuleSerializer(module, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated_module = edit_module(
            module=module,
            validated_data=serializer.validated_data
        )

        response_serializer = ModuleSerializer(updated_module)
        return Response({
            "message": "Módulo actualizado exitosamente.",
            "data": response_serializer.data
        }, status=status.HTTP_200_OK)

    def delete(self, request, id):
        try:
            module = delete_module(id)
            # serializer = ModuleSerializer(module)
            return Response({
                "message": "Módulo eliminnado exitosamente.",
                # "data": serializer.data
            }, status=status.HTTP_200_OK)
        except Http404:
            return Response({
                "message" : "El módulo que intentas eliminar no existe"
            }, status=status.HTTP_404_NOT_FOUND)

