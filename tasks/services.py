from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from account.models import User
from modules.models import Module, UserModule
from tasks.models import Tasks


def get_membership(module_id: int, user: User) -> UserModule:
    """
    Devuelve la relación del usuario con el módulo.
    Lanza PermissionError si el usuario no es integrante.
    """
    membership = UserModule.objects.filter(
        module_id=module_id,
        user=user
    ).first()

    if not membership:
        raise PermissionError("No perteneces a este módulo.")

    return membership


def validate_assignee(module_id: int, assignee: User | None) -> None:
    """
    El responsable de una tarea debe ser integrante del módulo (RN-11).
    """
    if assignee is None:
        return

    is_member = UserModule.objects.filter(
        module_id=module_id,
        user=assignee
    ).exists()

    if not is_member:
        raise ValidationError({
            "assignee_id": "El responsable debe ser integrante del módulo."
        })


def get_tasks_list(
    module_id: int,
    user: User,
    state: str | None = None,
    search: str | None = None
) -> QuerySet[Tasks]:
    """
    Retorna las tareas del módulo ordenadas de la más reciente a la más antigua.
    Permite filtrar por estado y buscar por título.
    """
    get_membership(module_id, user)

    queryset = Tasks.objects.filter(
        module_id=module_id
    ).select_related('assignee').order_by('-created_at')

    if state:
        valid_states = [choice[0] for choice in Tasks.TaskState.choices]
        if state not in valid_states:
            raise ValidationError({
                "estado": f"Estado inválido. Valores permitidos: {', '.join(valid_states)}."
            })
        queryset = queryset.filter(state=state)

    if search:
        queryset = queryset.filter(title__icontains=search.strip())

    return queryset


def create_task(module_id: int, user: User, validated_data: dict) -> Tasks:
    """
    Crea una tarea dentro del módulo. Cualquier integrante puede crearla (RF-16).
    La prioridad por defecto es MEDIA si no se especifica (RN-27).
    """
    get_membership(module_id, user)

    module = get_object_or_404(Module, id=module_id)
    assignee = validated_data.get('assignee')
    validate_assignee(module_id, assignee)

    return Tasks.objects.create(
        module=module,
        **validated_data
    )


def get_task(module_id: int, task_id: int, user: User) -> Tasks:
    get_membership(module_id, user)

    return get_object_or_404(
        Tasks.objects.select_related('assignee'),
        id=task_id,
        module_id=module_id
    )


def update_task(
    module_id: int,
    task_id: int,
    user: User,
    validated_data: dict
) -> Tasks:
    """
    Actualiza una tarea respetando las reglas de permisos:

    - OWNER: puede modificar cualquier tarea.
    - MEMBER: solo puede modificar tareas que tenga asignadas.
      También puede "tomar" una tarea sin asignar asignándosela a sí mismo (RF-19).
    """
    membership = get_membership(module_id, user)

    task = get_object_or_404(Tasks, id=task_id, module_id=module_id)

    if not membership.is_owner:
        is_assigned_to_user = task.assignee_id == user.id
        is_taking_unassigned = (
            task.assignee_id is None
            and validated_data.get('assignee') == user
        )

        if not is_assigned_to_user and not is_taking_unassigned:
            raise PermissionError(
                "Solo puedes modificar las tareas que tienes asignadas."
            )

    if 'assignee' in validated_data:
        validate_assignee(module_id, validated_data['assignee'])

    for field, value in validated_data.items():
        setattr(task, field, value)

    task.save()
    return task


def delete_task(module_id: int, task_id: int, user: User) -> None:
    """
    Elimina una tarea según los permisos:

    - OWNER: puede eliminar cualquier tarea.
    - MEMBER: solo tareas sin asignar o asignadas a él (RN-16).
    """
    membership = get_membership(module_id, user)

    task = get_object_or_404(Tasks, id=task_id, module_id=module_id)

    if not membership.is_owner and task.assignee_id not in (user.id, None):
        raise PermissionError(
            "No puedes eliminar una tarea asignada a otro integrante."
        )

    task.delete()
