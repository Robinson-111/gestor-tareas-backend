from django.db import transaction
from django.db.models import QuerySet
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from modules.models import Module, UserModule
from account.models import User


def get_modules_list() -> QuerySet[Module]:
    """
    Retorna todos los módulos del sistema ordenados del más reciente al más antiguo.
    Cualquier usuario tiene acceso a consultar la lista de módulos.
    """
    return Module.objects.all().select_related('creator').order_by('-created_at')


def create_module(creator: User, validated_data: dict) -> Module:
    """
    Crea un módulo y asigna automáticamente al creador como OWNER en UserModule
    de forma atómica.
    """
    members = validated_data.pop('members', [])

    with transaction.atomic():
        module = Module.objects.create(
            creator=creator,
            **validated_data
        )
        UserModule.objects.create(
            user=creator,
            module=module,
            rol=UserModule.Roles.OWNER
        )
    
        for user in members:
            if user == creator:
                continue

            UserModule.objects.create(
                user=user,
                module=module,
                rol=UserModule.Roles.MEMBER
            )

        return module


def get_module(id: int) -> Module:
    return get_object_or_404(Module.objects.select_related('creator'), id=id)


def edit_module(module: Module, validated_data: dict) -> Module:
    """
    Actualiza los campos de un módulo con los datos validados y guarda los cambios.
    """
    for field, value in validated_data.items():
        setattr(module, field, value)
    module.save()
    return module


def delete_module(id: int):
    module = get_object_or_404(Module, id=id)
    return module.delete()

def get_members_module(module_id: int):
    get_object_or_404(Module, id=module_id)
    return UserModule.objects.filter(module=module_id).select_related('user')


def add_member_to_module(module_id: int, user: User, rol: str = UserModule.Roles.MEMBER) -> UserModule:
    """
    Agrega un nuevo integrante a un módulo.
    Verifica que el módulo exista y que el usuario no esté asignado ya.
    """
    module = get_object_or_404(Module, id=module_id)

    if UserModule.objects.filter(module=module, user=user).exists():
        raise ValidationError({"user_id": ["El usuario ya es integrante de este módulo."]})

    return UserModule.objects.create(
        module=module,
        user=user,
        rol=rol
    )


def delete_member_from_module(module_id: int, user_id: int):
    """
    Elimina a un integrante de un módulo.
    No permite eliminar al propietario (OWNER) del módulo.
    """
    user_module = get_object_or_404(UserModule, module_id=module_id, user_id=user_id)
    if user_module.rol == UserModule.Roles.OWNER:
        raise ValidationError("No es posible eliminar al propietario del módulo.")
    user_module.delete()
    return user_module
