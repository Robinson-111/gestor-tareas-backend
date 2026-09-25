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


class UserModule(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_modules",
        verbose_name="Usuario"
    )
    module = models.ForeignKey(
        Module,
        on_delete=models.CASCADE,
        related_name="user_modules",
        verbose_name="Módulo"
    )

    class Roles(models.TextChoices):
        OWNER = 'OWNER', 'Propietario'
        MEMBER = 'MEMBER', 'Integrante'

    rol = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.MEMBER,
        null=False
    )

    @property
    def is_ower(self):
        return self.rol == self.Roles.OWNER
    
    def is_member(self):
        return self.rol == self.Roles.MEMBER

    class Meta:
        db_table = 'user_module'
        verbose_name = 'Usuario por Módulo'
        verbose_name_plural = 'Usuarios por Módulo'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'module'],
                name='unique_user_module'
            ),
            #validar en BD solo exista un owner por modulo
            models.UniqueConstraint(
                fields=['module'],
                condition=models.Q(rol='OWNER'),
                name='unique_owner_per_module'
            )
        ]

    def __str__(self):
        return f"{self.user.email} - {self.module.name} ({self.rol})"
