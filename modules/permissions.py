from rest_framework.exceptions import NotFound
from rest_framework.permissions import BasePermission

from modules.models import Module, UserModule


def _get_module_id_or_404(view) -> int:
    module_id = view.kwargs.get('id')

    if not module_id:
        raise NotFound("El módulo no existe.")

    if not Module.objects.filter(id=module_id).exists():
        raise NotFound("El módulo no existe.")

    return module_id


class IsModuleMember(BasePermission):
    """
    Permite el acceso únicamente a los integrantes del módulo indicado en la URL.
    """

    message = "No perteneces a este módulo."

    def has_permission(self, request, view):
        module_id = _get_module_id_or_404(view)

        return UserModule.objects.filter(
            module_id=module_id,
            user=request.user
        ).exists()


class IsModuleOwner(BasePermission):
    """
    Permite el acceso únicamente al OWNER del módulo indicado en la URL.
    """

    message = "Solo el OWNER puede realizar esta acción."

    def has_permission(self, request, view):
        module_id = _get_module_id_or_404(view)

        return UserModule.objects.filter(
            module_id=module_id,
            user=request.user,
            rol=UserModule.Roles.OWNER
        ).exists()
