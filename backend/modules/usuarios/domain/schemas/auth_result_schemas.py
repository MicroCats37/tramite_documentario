"""
Esquemas de resultado de dominio para Auth — DTOs internos usados por servicios, NO esquemas HTTP.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel


class AreaAsignadaResult(BaseModel):
    """DTO interno para un área asignada vigente."""
    id: uuid.UUID
    area_id: uuid.UUID
    area_nombre: str
    cargo_id: uuid.UUID
    cargo_nombre: str


class UserDatosResult(BaseModel):
    """DTO interno con datos básicos del usuario (sin áreas)."""
    id: uuid.UUID
    username: str
    dni: str | None
    email: str | None
    nombres: str | None
    apellidos: str | None
    is_staff: bool
    is_superuser: bool


class AuthUserResult(BaseModel):
    """DTO de resultado interno con datos de usuario y áreas asignadas vigentes."""
    datos: UserDatosResult
    areas_asignadas_vigentes: list[AreaAsignadaResult]


class LoginTokenResult(BaseModel):
    """DTO de resultado para operaciones de login — contiene tokens y datos del usuario."""
    access_token: str
    refresh_token: str
    expires_at: datetime
    user: AuthUserResult
