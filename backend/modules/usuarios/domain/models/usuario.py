"""
Usuario — Custom user model with flexible username (DNI or area slug).
Extends AbstractBaseUser + PermissionsMixin following the project pattern.
"""

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.core.validators import RegexValidator
from simple_history.models import HistoricalRecords

from core.models import BaseModel, DjangoAuthMixin


class UsuarioManager(BaseUserManager):
    """Custom manager for Usuario model."""

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError("El campo username debe estar establecido.")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, password, **extra_fields)


# Validador de DNI: exactamente 8 dígitos (solo cuando dni tiene valor)
dni_validator = RegexValidator(
    regex=r"^\d{8}$",
    message="El DNI debe contener exactamente 8 dígitos numéricos.",
    code="invalid_dni",
)


class Usuario(AbstractBaseUser, PermissionsMixin, DjangoAuthMixin, BaseModel):
    history = HistoricalRecords()
    """
    Usuario customizado con AbstractBaseUser + PermissionsMixin.
    username puede ser un DNI de 8 dígitos o un slug de área en snake_case.
    dni y email son opcionales.
    """
    nombres = models.CharField(max_length=255, blank=True, null=True, verbose_name="Nombre")
    apellidos = models.CharField(max_length=255, blank=True, null=True, verbose_name="Apellido")
    email = models.EmailField(
        max_length=255,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Correo electrónico",
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        verbose_name="Nombre de usuario",
        help_text="DNI de 8 dígitos o slug de área en snake_case.",
    )
    dni = models.CharField(
        max_length=8,
        unique=True,
        validators=[dni_validator],
        blank=True,
        null=True,
        verbose_name="DNI",
        help_text="8 dígitos numéricos exactamente (opcional).",
    )

    # Hereda de AbstractBaseUser: password, last_login, is_active
    # Hereda de PermissionsMixin: groups, user_permissions, is_superuser
    # Hereda de DjangoAuthMixin: is_staff
    # Hereda de BaseModel: id (UUID), created_at, updated_at

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []

    objects = UsuarioManager()

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Usuario {self.dni}"