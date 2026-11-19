from django.conf import settings
from django.db import models


class Notification(models.Model):
    """
    Notificación persistida de un usuario.

    Cada fila pertenece a un único destinatario. El `payload` guarda las
    referencias necesarias para navegar desde la campana (tarea y/o módulo)
    sin acoplar el modelo a `tasks` o `modules`.
    """

    class Type(models.TextChoices):
        TASK_ASSIGNED = 'TASK_ASSIGNED', 'Tarea asignada'
        TASK_UNASSIGNED = 'TASK_UNASSIGNED', 'Tarea desasignada'
        TASK_COMPLETED = 'TASK_COMPLETED', 'Tarea completada'
        TASK_CREATED = 'TASK_CREATED', 'Tarea creada'
        TASK_DELETED = 'TASK_DELETED', 'Tarea eliminada'
        MEMBER_ADDED = 'MEMBER_ADDED', 'Integrante agregado'
        MEMBER_REMOVED = 'MEMBER_REMOVED', 'Integrante eliminado'
        OWNER_TRANSFERRED = 'OWNER_TRANSFERRED', 'Propiedad transferida'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    type = models.CharField(max_length=32, choices=Type.choices)
    title = models.CharField(max_length=150)
    message = models.CharField(max_length=255, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(
                fields=['user', 'is_read', '-created_at'],
                name='notif_user_read_created'
            )
        ]

    def __str__(self):
        return f'{self.type} → {self.user_id}: {self.title}'
