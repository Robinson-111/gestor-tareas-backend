from django.db import models
from account.models import User
from modules.models import Module

class Tasks(models.Model):
    title = models.CharField(max_length=150, null=False)
    description = models.TextField(blank=True, null=True)

    class TaskPriority(models.TextChoices):
        BAJA = 'BAJA', 'Baja'
        MEDIA = 'MEDIA', 'Media'
        ALTA = 'ALTA', 'Alta'


    priority = models.CharField(
        max_length=20,
        choices=TaskPriority.choices,
        default=TaskPriority.MEDIA
    )

    class TaskState(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        EN_CURSO = 'EN_CURSO', 'En Curso'
        COMPLETADA = 'COMPLETADA', 'Completada'
    
    state = models.CharField(
        max_length=20,
        choices=TaskState.choices,
        default=TaskState.PENDIENTE
    )

    assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name="tasks",
        verbose_name="Responsable",
        db_column="assignee_id"
    )

    module = models.ForeignKey(
        Module,
        on_delete= models.CASCADE,
        null=False,
        related_name="tasks",
        verbose_name="Módulo",
        db_column="module_id"
        
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'task'
        verbose_name = 'Tarea'
        verbose_name_plural = 'Tareas'
   
   
    def __str__(self):
        return self.title