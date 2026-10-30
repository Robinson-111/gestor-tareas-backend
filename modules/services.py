from django.db import transaction
from django.db.models import QuerySet, Q
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404

from modules.models import Module, UserModule
from account.models import User
from tasks.models import Tasks


def get_modules_list(search: str | None = None) -> QuerySet[Module]:
    """
    Retorna todos los módulos del sistema ordenados del más reciente al más antiguo.
    Si se proporciona el parámetro search, filtra por nombre o descripción.
    """
    queryset = Module.objects.all().select_related('creator').order_by('-created_at')

    if search:
        search = search.strip()
        queryset = queryset.filter(
            Q(name__icontains=search) | Q(description__icontains=search)
        )

    return queryset


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
    Un módulo solo puede pasar a COMPLETADO si tiene al menos una tarea
    y todas sus tareas están COMPLETADAS.
    """
    new_state = validated_data.get('state')

    if new_state == Module.ModuleStates.COMPLETADO:
        if not module.tasks.exists():
            raise ValidationError({
                "state": "No se puede pasar el módulo a COMPLETADO porque no tiene ninguna tarea asociada."
            })

        if module.tasks.exclude(state=Tasks.TaskState.COMPLETADA).exists():
            raise ValidationError({
                "state": "No se puede pasar el módulo a COMPLETADO hasta que todas sus tareas estén COMPLETADAS."
            })

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


def edit_rol_member_from_module(
    module_id: int,
    user_id: int,
    current_user_id: int
):
    """
    Transfiere el rol de OWNER a otro miembro del módulo.

    Solo el OWNER actual puede realizar la transferencia.
    """

    current_owner = UserModule.objects.filter(
        module_id=module_id,
        user_id=current_user_id
    ).first()

    if not current_owner:
        raise ValueError("El usuario no pertenece al módulo.")

    if not current_owner.is_owner:
        raise PermissionError(
            "Solo el OWNER puede transferir el rol."
        )

    member = UserModule.objects.filter(
        module_id=module_id,
        user_id=user_id
    ).first()

    if not member:
        raise ValueError(
            "El usuario no pertenece al módulo."
        )

    if not member.is_member:
        raise ValueError(
            "El usuario seleccionado ya es OWNER."
        )

    with transaction.atomic():

        current_owner.rol = UserModule.Roles.MEMBER
        current_owner.save(update_fields=['rol'])

        member.rol = UserModule.Roles.OWNER
        member.save(update_fields=['rol'])

    return member


def claim_module_ownership(module_id: int, user_id: int) -> UserModule:
    """
    Permite a un integrante reclamar el rol de OWNER
    si el módulo no tiene ningún propietario asignado.
    """
    get_object_or_404(Module, id=module_id)

    # Verificar que NO haya owner
    owner_exists = UserModule.objects.filter(
        module_id=module_id,
        rol=UserModule.Roles.OWNER
    ).exists()


    if owner_exists:
        raise PermissionError("El módulo ya tiene un propietario.")

    
    #Validamos si el reclamador es integrante del modulo, de lo contrario lo incorparamos
    member = UserModule.objects.filter(
        module_id=module_id,
        user_id=user_id
    ).first()

    if not member:
        member = UserModule.objects.create(
            module_id=module_id,
            user_id=user_id,
            rol=UserModule.Roles.OWNER
        )
        return member

    member.rol = UserModule.Roles.OWNER
    member.save(update_fields=['rol'])

    return member
