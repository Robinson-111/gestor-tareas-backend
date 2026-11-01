from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models


class UserManager(BaseUserManager):
    """Manager del modelo User (email como identificador)."""

    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError('El usuario debe tener un correo electrónico')

        email = self.normalize_email(email)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)  # Hash de la contraseña
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields.setdefault('rol', User.Roles.SUPER_ADMIN)
        return self.create_user(email, name, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    # ------------------------------------------------------------------
    # Roles
    # ------------------------------------------------------------------
    class Roles(models.TextChoices):
        SUPER_ADMIN = 'SUPER_ADMIN', 'Super Administrador'
        ADMIN = 'ADMIN', 'Administrador'
        USER = 'USER', 'Usuario Regular'

    # ------------------------------------------------------------------
    # Campos de identidad
    # ------------------------------------------------------------------
    name_validator = RegexValidator(
        regex=r'^[a-zA-ZáéíóúÁÉÍÓÚñÑ\s]+$',
        message='El nombre solo puede contener letras y espacios.'
    )

    name = models.CharField(max_length=150, validators=[name_validator])
    email = models.EmailField(max_length=150, unique=True)

    # ------------------------------------------------------------------
    # Rol
    # ------------------------------------------------------------------
    rol = models.CharField(
        max_length=20,
        choices=Roles.choices,
        default=Roles.USER
    )

    # ------------------------------------------------------------------
    # Flags de acceso
    # (is_superuser, groups y user_permissions vienen de PermissionsMixin)
    # ------------------------------------------------------------------
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    # ------------------------------------------------------------------
    # Auditoría
    # ------------------------------------------------------------------
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ------------------------------------------------------------------
    # Configuración de autenticación
    # ------------------------------------------------------------------
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    class Meta:
        db_table = 'user'

    def __str__(self):
        return self.email

    # ------------------------------------------------------------------
    # Propiedades de rol
    # ------------------------------------------------------------------
    @property
    def is_super_admin(self):
        return self.rol == self.Roles.SUPER_ADMIN

    @property
    def is_admin(self):
        return self.rol == self.Roles.ADMIN

    @property
    def is_regular_user(self):
        return self.rol == self.Roles.USER

    @property
    def is_admin_or_super(self):
        return self.rol in (self.Roles.ADMIN, self.Roles.SUPER_ADMIN)

    # ------------------------------------------------------------------
    # Sincronización rol -> flags de acceso
    # ------------------------------------------------------------------
    def save(self, *args, **kwargs):
        self.is_staff = self.is_super_admin
        self.is_superuser = self.is_super_admin
        super().save(*args, **kwargs)