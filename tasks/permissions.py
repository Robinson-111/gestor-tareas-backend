from rest_framework.permissions import BasePermission
from rest_framework.exceptions import NotFound

from modules.models import Module, UserModule


class IsModuleMember(BasePermission):
    """
    Permite el acceso únicamente a los integrantes del módulo indicado en la URL.
    """

    message = "No perteneces a este módulo."

    def has_permission(self, request, view):
        module_id = view.kwargs.get('id')

        if not module_id:
            return False

        if not Module.objects.filter(id=module_id).exists():
            raise NotFound("El módulo no existe.")

        return UserModule.objects.filter(
            module_id=module_id,
            user=request.user
        ).exists()
