from django.db.models import QuerySet
from modules.models import Module


def get_modules_list() -> QuerySet[Module]:
    """
    Retorna todos los módulos del sistema ordenados del más reciente al más antiguo.
    Cualquier usuario tiene acceso a consultar la lista de módulos.
    """
    return Module.objects.all().select_related('creator').order_by('-created_at')
