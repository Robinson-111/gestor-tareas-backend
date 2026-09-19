from django.db import models
from account.models import User

class Module(models.Model):

    name = models.CharField(max_length=150, null=False)
    description = models.TextField(null=True, blank=True)
    
    #Definimos los estados del modulo "ENUM"
    class ModuleStates(models.TextChoices):
        PENDIENTE = 'PENDIENTE', 'Pendiente'
        EN_CURSO = 'EN_CURSO', 'En Curso'
        COMPLETADO = 'COMPLETADO', 'Completado'
    
    state = models.CharField(
        max_length=20,
        choices=ModuleStates.choices,
        default=ModuleStates.PENDIENTE)

    creator = models.ForeignKey(
        User,   # Modelo donde se encuentra el PK que queremos enlazar
        on_delete=models.SET_NULL,  # Al borrar user, cambia a null
        null=True,
        verbose_name="Creador",
        related_name="created_modules"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'module'
        verbose_name = 'Módulo'
        verbose_name_plural = 'Módulos'
   
   
    def __str__(self):
        return self.name


