"""
Esquemas HTTP response para UsuarioMencionable — Schema Ninja para API.
"""
import uuid

from ninja import Field

from core.types import BaseSchema


class UsuarioMencionableOut(BaseSchema):
    """
    Respuesta HTTP para un usuario mencionable en contexto de chat.

    Incluye los campos mínimos necesarios para el selector de menciones:
    id, username, nombres, apellidos, dni.

    Cuando se consulta por solicitud_id, se incluyen además campos de contexto
    derivados de la participación en períodos abiertos de la solicitud:
    area_id, area_nombre, rol, periodo_id, numero_ciclo, tipo_participacion.
    """

    id: uuid.UUID = Field(..., description="ID único del usuario")
    username: str = Field(..., description="Nombre de usuario (DNI)")
    nombres: str | None = Field(None, description="Nombres del usuario")
    apellidos: str | None = Field(None, description="Apellidos del usuario")
    dni: str | None = Field(None, description="DNI del usuario")
    # ── Contexto de participación (solo cuando se consulta por solicitud_id) ──
    area_id: uuid.UUID | None = Field(
        None,
        description="ID del área donde el usuario participa (contexto solicitud)",
    )
    area_nombre: str | None = Field(
        None,
        description="Nombre del área donde el usuario participa (contexto solicitud)",
    )
    rol: str | None = Field(
        None,
        description="Rol del usuario en el período (Responsable, colaborador, etc.)",
    )
    periodo_id: uuid.UUID | None = Field(
        None,
        description="ID del período de participación (contexto solicitud)",
    )
    numero_ciclo: int | None = Field(
        None,
        description="Número de ciclo del período (1, 2, 3...)",
    )
    tipo_participacion: str | None = Field(
        None,
        description="Tipo de participación: PRINCIPAL o ADJUNTA",
    )
