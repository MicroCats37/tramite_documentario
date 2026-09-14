"""
UsuarioMencionableController — controlador HTTP ligero para consulta de usuarios mencionables.

Responsabilidades:
- Recibir requests HTTP y delegar al selector.
- Authentication via JWT (IsAuthenticated).
- NO lógica de negocio.

Patrón async: controller async → selector (sync).
"""
from uuid import UUID

from asgiref.sync import sync_to_async
from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated
from ninja import Query

from core.responses import ApiResponse, success_response
from modules.usuarios.infrastructure.selectors import (
    UsuarioMencionableSelector,
    UsuarioMencionableCtx,
)
from modules.usuarios.presentation.schemas.usuario_mencionable_schemas import (
    UsuarioMencionableOut,
)


@api_controller(
    "/usuarios",
    tags=["Usuarios"],
    permissions=[IsAuthenticated],
)
class UsuarioMencionableController:
    """
    Controlador para consulta de usuarios mencionables en contexto de solicitud/área.

    Endpoints:
    - GET /usuarios/mencionables/ — Lista usuarios mencionables
    """

    @route.get(
        "/mencionables/",
        response={200: ApiResponse[list[UsuarioMencionableOut]]},
    )
    async def listar_mencionables(
        self,
        request,
        solicitud_id: UUID | None = Query(
            None,
            description="UUID de la solicitud (prioritario — usa participantes de períodos abiertos)",
        ),
        periodo_id: UUID | None = Query(
            None,
            description="UUID del período (opcional — estrecha resultados a un período específico)",
        ),
        conversacion_id: UUID | None = Query(
            None,
            description="UUID de la conversación (derive solicitud)",
        ),
        area_id: UUID | None = Query(
            None,
            description="UUID del área (filtro explícito — usa AsignacionUsuario global)",
        ),
        nombre: str | None = Query(
            None,
            description="Texto de búsqueda por nombres, apellidos, username o dni",
        ),
    ):
        """
        Lista usuarios mencionables en el contexto de una solicitud o área.

        Un usuario es mencionable si tiene una asignación activa a un área
        que está asignada a la solicitud.

            Args:
                solicitud_id: UUID de la solicitud (prioritario).
                conversacion_id: UUID de la conversación (deriva solicitud).
                area_id: UUID del área (filtro explícito).
                nombre: Texto de búsqueda por nombres, apellidos, username o dni.

        Returns:
            Lista de usuarios mencionables ordenados por nombres/apellidos.
        """
        def _fetch():
            return UsuarioMencionableSelector.listar_mencionables(
                solicitud_id=solicitud_id,
                area_id=area_id,
                periodo_id=periodo_id,
                conversacion_id=conversacion_id,
                nombre=nombre,
            )

        resultado = await sync_to_async(_fetch, thread_sensitive=True)()

        # Para solicitud_id: list[UsuarioMencionableCtx] — respuesta enriquecida
        if isinstance(resultado, list):
            outs = []
            for ctx in resultado:
                # Defensive: ensure ctx.usuario is a valid Usuario with id
                # before accessing nested attributes
                usuario = ctx.usuario
                if usuario is None or not hasattr(usuario, "id"):
                    continue
                outs.append(
                    UsuarioMencionableOut(
                        id=usuario.id,
                        username=usuario.username,
                        nombres=usuario.nombres,
                        apellidos=usuario.apellidos,
                        dni=usuario.dni,
                        area_id=ctx.area_id,
                        area_nombre=ctx.area_nombre,
                        rol=ctx.rol,
                        periodo_id=ctx.periodo_id,
                        numero_ciclo=ctx.numero_ciclo,
                        tipo_participacion=ctx.tipo_participacion,
                    )
                )
        else:
            # Para area_id: QuerySet[Usuario] — respuesta básica
            usuarios = list(resultado)
            outs = [
                UsuarioMencionableOut(
                    id=u.id,
                    username=u.username,
                    nombres=u.nombres,
                    apellidos=u.apellidos,
                    dni=u.dni,
                )
                for u in usuarios
            ]

        return success_response(outs)
