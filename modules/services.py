from django.db import transaction
from django.db.models import QuerySet
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
