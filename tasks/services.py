from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from account.models import User
from modules.models import Module, UserModule
from notifications.models import Notification
from notifications.services import notify, notify_many
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

    task = Tasks.objects.create(
        module=module,
        **validated_data
    )
    _notify_task_created(task, module, user)

    return task


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
    - MEMBER responsable: puede modificar la tarea que tiene asignada.
    - MEMBER sin tarea asignada: solo puede "tomar" una tarea sin
      responsable asignándosela a sí mismo (RF-19). En esa toma no puede
      cambiar ningún otro campo (solo se acompaña de `state=EN_CURSO`,
      que forma parte de la toma). El resto de campos queda bloqueado
      hasta ser el responsable.
    """
    membership = get_membership(module_id, user)

    task = get_object_or_404(Tasks, id=task_id, module_id=module_id)
    old_assignee_id = task.assignee_id
    old_state = task.state

    if not membership.is_owner:
        is_responsible = task.assignee_id == user.id
        is_claiming_unassigned = (
            task.assignee_id is None
            and validated_data.get('assignee') == user
        )

        if is_claiming_unassigned:
            forbidden_fields = [
                field
                for field, value in validated_data.items()
                if field != 'assignee'
                and not (field == 'state' and value == 'EN_CURSO')
            ]
            if forbidden_fields:
                raise PermissionError(
                    "Solo el responsable puede editar los campos de una tarea."
                )
        elif not is_responsible:
            raise PermissionError(
                "Solo el responsable puede editar los campos de una tarea."
            )

    if 'assignee' in validated_data:
        validate_assignee(module_id, validated_data['assignee'])

    for field, value in validated_data.items():
        setattr(task, field, value)

    task.save()
    _notify_task_updated(task, user, old_assignee_id, old_state)
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

    module = task.module
    title = task.title
    task.delete()
    _notify_task_deleted(module, title, user)


def _task_payload(task: Tasks) -> dict:
    return {'task_id': task.id, 'module_id': task.module_id}


def _notify_task_created(task: Tasks, module: Module, actor: User) -> None:
    assignee_id = task.assignee_id

    if assignee_id and assignee_id != actor.id:
        notify(
            task.assignee,
            Notification.Type.TASK_ASSIGNED,
            f'Te asignaron «{task.title}»',
            f'{actor.name} te asignó una tarea en {module.name}.',
            _task_payload(task),
        )

    recipients = [
        membership.user
        for membership in UserModule.objects
        .filter(module=module)
        .select_related('user')
        if membership.user_id not in (actor.id, assignee_id)
    ]
    notify_many(
        recipients,
        Notification.Type.TASK_CREATED,
        f'Nueva tarea en {module.name}',
        f'{actor.name} creó «{task.title}».',
        _task_payload(task),
        exclude_user_ids=(actor.id, assignee_id),
    )


def _notify_task_updated(
    task: Tasks,
    actor: User,
    old_assignee_id: int | None,
    old_state: str
) -> None:
    module = task.module
    new_assignee_id = task.assignee_id

    if new_assignee_id != old_assignee_id:
        if new_assignee_id and new_assignee_id != actor.id:
            notify(
                task.assignee,
                Notification.Type.TASK_ASSIGNED,
                f'Te asignaron «{task.title}»',
                f'{actor.name} te asignó una tarea en {module.name}.',
                _task_payload(task),
            )

        if old_assignee_id and old_assignee_id != actor.id:
            previous = User.objects.filter(id=old_assignee_id).first()
            if previous:
                notify(
                    previous,
                    Notification.Type.TASK_UNASSIGNED,
                    f'Te quitaron «{task.title}»',
                    f'{actor.name} te desasignó una tarea en {module.name}.',
                    _task_payload(task),
                )

    if (
        old_state != Tasks.TaskState.COMPLETADA
        and task.state == Tasks.TaskState.COMPLETADA
    ):
        owners = [
            membership.user
            for membership in UserModule.objects
            .filter(module=module, rol=UserModule.Roles.OWNER)
            .select_related('user')
            if membership.user_id != actor.id
        ]
        notify_many(
            owners,
            Notification.Type.TASK_COMPLETED,
            f'Tarea completada en {module.name}',
            f'{actor.name} completó «{task.title}».',
            _task_payload(task),
            exclude_user_ids=(actor.id,),
        )


def _notify_task_deleted(module: Module, title: str, actor: User) -> None:
    recipients = [
        membership.user
        for membership in UserModule.objects
        .filter(module=module)
        .select_related('user')
        if membership.user_id != actor.id
    ]
    notify_many(
        recipients,
        Notification.Type.TASK_DELETED,
        f'Tarea eliminada en {module.name}',
        f'{actor.name} eliminó «{title}».',
        {'module_id': module.id},
        exclude_user_ids=(actor.id,),
    )
