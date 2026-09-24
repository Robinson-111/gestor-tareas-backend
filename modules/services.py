from django.db import transaction
from django.db.models import QuerySet
from modules.models import Module, UserModule
from account.models import User
from django.shortcuts import get_object_or_404


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

