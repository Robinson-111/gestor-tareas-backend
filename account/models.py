from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import RegexValidator

# Manager personalizado requerido al usar AbstractBaseUser
class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError('El usuario debe tener un correo electrónico')
        
        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password) # Encripta (hash) la contraseña
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault('rol', User.Roles.SUPER_ADMIN)
        return self.create_user(email, name, password, **extra_fields)

class User(AbstractBaseUser):
    # id: Django crea automáticamente un BigAutoField (BIGINT PK) 
    # si en settings.py tienes DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

    # name: VARCHAR(150) sin caracteres especiales
    name_validator = RegexValidator(
        regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
        message='El nombre solo puede contener letras y espacios.'
    )
    name = models.CharField(max_length=150, validators=[name_validator])

    # email: VARCHAR(150) UNIQUE
    email = models.EmailField(max_length=150, unique=True)

    # password: Ya está incluido por AbstractBaseUser como VARCHAR(128) con hash
    
    # rol: ENUM (Implementado como CharField con choices por compatibilidad en Django)
    class Roles(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Administrador'
        ADMIN = 'ADMIN', 'Administrador'
        USER = 'USER', 'Usuario Regular'
        
    rol = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.USER
    )
    
    # created_at y updated_at: DATETIME
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager() # Vinculamos el manager

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name'] # Requerido al crear superusers por consola

    def __str__(self):
        return self.email
