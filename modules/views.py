from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.http import Http404

from .services import (
    get_modules_list,
    create_module,
    get_module,
    edit_module,
    delete_module,
    get_members_module,
    add_member_to_module,
    delete_member_from_module,
)
from .serializers.modules import ModuleSerializer
from .serializers.module_create import ModuleCreateSerializer
from .serializers.members_module import MemberModuleSerializer
from .serializers.add_member import AddMemberModuleSerializer


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

class MembersModuleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id):
        try:
            members = get_members_module(id)
            serializer = MemberModuleSerializer(members, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Http404:
            return Response({
                "message": "El módulo no existe."
            }, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, id):
        serializer = AddMemberModuleSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            member = add_member_to_module(
                module_id=id,
                user=serializer.validated_data['user'],
                rol=serializer.validated_data.get('rol')
            )
            response_serializer = MemberModuleSerializer(member)
            return Response({
                "message": "Integrante agregado exitosamente.",
                "data": response_serializer.data
            }, status=status.HTTP_201_CREATED)
        except Http404:
            return Response({
                "message": "El módulo no existe."
            }, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, id, user_id=None):
        if not user_id:
            return Response({
                "message": "Debe especificar el user_id del integrante a eliminar."
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            delete_member_from_module(module_id=id, user_id=user_id)
            return Response({
                "message": "Integrante eliminado exitosamente del módulo."
            }, status=status.HTTP_200_OK)
        except Http404:
            return Response({
                "message": "El integrante no pertenece a este módulo o no existe."
            }, status=status.HTTP_404_NOT_FOUND)
        except ValidationError as e:
            return Response({
                "message": e.detail if isinstance(e.detail, str) else e.detail[0] if isinstance(e.detail, list) else str(e.detail)
            }, status=status.HTTP_400_BAD_REQUEST)
