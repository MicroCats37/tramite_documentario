"""
Esquemas HTTP request/response para Auth — Schema Ninja para API.
"""
import uuid
from datetime import datetime
from ninja import Field
from core.types import BaseSchema


class LoginUsernameIn(BaseSchema):
    """Payload de login con username + password."""
    username: str = Field(..., min_length=1, description="Nombre de usuario")
    password: str = Field(..., min_length=1, description="Contraseña")


class LoginDniIn(BaseSchema):
    """Payload de login con DNI + password."""
    dni: str = Field(..., min_length=8, max_length=8, description="DNI de 8 dígitos")
    password: str = Field(..., min_length=1, description="Contraseña")


class LoginEmailIn(BaseSchema):
    """Payload de login con email + password."""
    email: str = Field(..., description="Correo electrónico")
    password: str = Field(..., min_length=1, description="Contraseña")


class UserDatosOut(BaseSchema):
    """Datos básicos del usuario en respuesta de login."""
    id: uuid.UUID = Field(..., description="ID único del usuario")
    username: str = Field(..., description="Nombre de usuario")
    dni: str | None = Field(None, description="DNI")
    email: str | None = Field(None, description="Correo electrónico")
    nombres: str | None = Field(None, description="Nombres")
    apellidos: str | None = Field(None, description="Apellidos")
    is_staff: bool = Field(..., description="Es staff")
    is_superuser: bool = Field(..., description="Es superusuario")


class AreaAsignadaOut(BaseSchema):
    """Área asignada vigente al usuario."""
    id: uuid.UUID = Field(..., description="ID de la asignación")
    area_id: uuid.UUID = Field(..., description="ID del área")
    area_nombre: str = Field(..., description="Nombre del área")
    cargo_id: uuid.UUID = Field(..., description="ID del cargo")
    cargo_nombre: str = Field(..., description="Nombre del cargo")


class AuthUserOut(BaseSchema):
    """Respuesta de usuario autenticado con datos y áreas asignadas vigentes."""
    datos: UserDatosOut = Field(..., description="Datos básicos del usuario")
    areas_asignadas_vigentes: list[AreaAsignadaOut] = Field(
        ..., description="Áreas asignadas vigentes del usuario"
    )


class LoginTokenOut(BaseSchema):
    """Respuesta de login con tokens y datos del usuario."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    expires_at: datetime = Field(..., description="Fecha/hora de expiración del access token (ISO 8601)")
    user: AuthUserOut = Field(..., description="Datos del usuario autenticado")
