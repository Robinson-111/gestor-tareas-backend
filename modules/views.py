from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from django.http import Http404

from .permissions import IsModuleMember, IsModuleOwner
from .services import (
    get_modules_list,
    get_explore_modules,
    get_claimable_modules,
    join_module,
    create_module,
    get_module,
    edit_module,
    delete_module,
    get_members_module,
    add_member_to_module,
    delete_member_from_module,
    edit_rol_member_from_module,
    claim_module_ownership,
    leave_module
)
from core.pagination import CustomPagination
from .serializers.modules import ModuleSerializer
from .serializers.explore_module import ExploreModuleSerializer
from .serializers.module_create import ModuleCreateSerializer
from .serializers.edit_modules import EditModuleSerializer
from .serializers.members_module import MemberModuleSerializer
from .serializers.add_member import AddMemberModuleSerializer


class ModuleListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        search = request.query_params.get('search')
        modules = get_modules_list(user=request.user, search=search)

        paginator = CustomPagination()
        paginated_modules = paginator.paginate_queryset(modules, request)
        serializer = ModuleSerializer(paginated_modules, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        serializer = ModuleCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        module = create_module(
            creator=request.user,
            validated_data=serializer.validated_data
        )

        response_serializer = ModuleSerializer(module)
        return Response({
            "message": "Módulo creado exitosamente.",
            "data": response_serializer.data
        }, status=status.HTTP_201_CREATED)


class ModuleExploreListView(APIView):
    """
    Módulos en los que el usuario no participa, para poder unirse como MEMBER.
    Incluye `has_owner` para distinguir los que también se pueden reclamar.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        search = request.query_params.get('search')
        modules = get_explore_modules(user=request.user, search=search)

        paginator = CustomPagination()
        paginated_modules = paginator.paginate_queryset(modules, request)
        serializer = ExploreModuleSerializer(paginated_modules, many=True)
        return paginator.get_paginated_response(serializer.data)


class ModuleJoinView(APIView):
    """
    Permite que un usuario autenticado se una por su cuenta a un módulo como
    MEMBER.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        try:
            member = join_module(module_id=id, user=request.user)
        except Http404:
            raise NotFound("El módulo no existe.")

        response_serializer = MemberModuleSerializer(member)
        return Response({
            "message": "Te has unido al módulo exitosamente.",
            "data": response_serializer.data
        }, status=status.HTTP_201_CREATED)


class ModuleClaimableListView(APIView):
    """
    Módulos sin OWNER que cualquier usuario registrado puede reclamar (RF-15).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        search = request.query_params.get('search')
        modules = get_claimable_modules(search=search)

        paginator = CustomPagination()
        paginated_modules = paginator.paginate_queryset(modules, request)
        serializer = ModuleSerializer(paginated_modules, many=True)
        return paginator.get_paginated_response(serializer.data)


class ModuleDetailView(APIView):
    def get_permissions(self):
        if self.request.method in ('PATCH', 'DELETE'):
            return [IsAuthenticated(), IsModuleOwner()]
        return [IsAuthenticated(), IsModuleMember()]

    def get(self, request, id):
        module = get_module(id)
        serializer = ModuleSerializer(module)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, id):
        module = get_module(id)
        serializer = EditModuleSerializer(module, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

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
            delete_module(id)
        except Http404:
            raise NotFound("El módulo que intentas eliminar no existe")

        return Response({
            "message": "Módulo eliminnado exitosamente.",
        }, status=status.HTTP_200_OK)


class MembersModuleView(APIView):
    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated(), IsModuleMember()]
        return [IsAuthenticated(), IsModuleOwner()]

    def get(self, request, id):
        try:
            members = get_members_module(id)
        except Http404:
            raise NotFound("El módulo no existe.")

        serializer = MemberModuleSerializer(members, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, id):
        serializer = AddMemberModuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            member = add_member_to_module(
                module_id=id,
                user=serializer.validated_data['user']
            )
        except Http404:
            raise NotFound("El módulo no existe.")

        response_serializer = MemberModuleSerializer(member)
        return Response({
            "message": "Integrante agregado exitosamente.",
            "data": response_serializer.data
        }, status=status.HTTP_201_CREATED)

    def delete(self, request, id, user_id=None):
        if not user_id:
            raise ValidationError(
                "Debe especificar el user_id del integrante a eliminar."
            )

        try:
            delete_member_from_module(module_id=id, user_id=user_id)
        except Http404:
            raise NotFound("El integrante no pertenece a este módulo o no existe.")

        return Response({
            "message": "Integrante eliminado exitosamente del módulo."
        }, status=status.HTTP_200_OK)

    def patch(self, request, id, user_id=None):
        target_user_id = user_id or request.data.get('user_id')
        if not target_user_id:
            raise ValidationError("Debe especificar el user_id del integrante.")

        try:
            member = edit_rol_member_from_module(
                module_id=id,
                user_id=target_user_id,
                current_user_id=request.user.id
            )
        except PermissionError as e:
            raise PermissionDenied(str(e))
        except ValueError as e:
            raise ValidationError(str(e))
        except Http404:
            raise NotFound("El módulo no existe.")

        response_serializer = MemberModuleSerializer(member)
        return Response({
            "message": "Rol transferido exitosamente.",
            "data": response_serializer.data
        }, status=status.HTTP_200_OK)


class ClaimModuleOwnershipView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, id):
        try:
            member = claim_module_ownership(
                module_id=id,
                user_id=request.user.id
            )
        except PermissionError as e:
            raise PermissionDenied(str(e))
        except ValueError as e:
            raise ValidationError(str(e))
        except Http404:
            raise NotFound("El módulo no existe.")

        response_serializer = MemberModuleSerializer(member)
        return Response({
            "message": "Has reclamado el rol de OWNER existosamente.",
            "data": response_serializer.data
        }, status=status.HTTP_200_OK)


class LeaveModuleView(APIView):
    """
    Permite a un MEMBER abandonar voluntariamente un módulo (RF-21).
    """

    permission_classes = [IsAuthenticated, IsModuleMember]

    def post(self, request, id):
        try:
            leave_module(module_id=id, user=request.user)
        except Http404:
            raise NotFound("El módulo no existe.")

        return Response({
            "message": "Has abandonado el módulo exitosamente."
        }, status=status.HTTP_200_OK)
