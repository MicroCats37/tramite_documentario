"""
Instancia central de NinjaExtraAPI.
Aquí se registran todos los routers y controllers del proyecto.
"""

from ninja_extra import NinjaExtraAPI
from ninja_jwt.authentication import JWTAuth
from ninja_jwt.controller import NinjaJWTDefaultController

from core.exceptions import register_exception_handlers
from modules.usuarios.presentation.controllers.auth_controller import AuthLoginController
from modules.usuarios.presentation.controllers.auth_me_controller import AuthMeController
from modules.usuarios.presentation.controllers.ingeniero_habilitado_controller import IngenieroHabilitadoController
from modules.usuarios.presentation.controllers.area_controller import AreaController
from modules.usuarios.presentation.controllers.usuario_mencionable_controller import (
    UsuarioMencionableController,
)
from modules.tramites.presentation.controllers.expediente_controller import ExpedienteController
from modules.tramites.presentation.controllers.solicitud_controller import SolicitudController
from modules.tramites.presentation.controllers.tipo_documento_controller import TipoDocumentoController
from modules.notificaciones.presentation.controllers.notificacion_controller import NotificacionController
from modules.asignaciones.presentation.controllers.periodo_controller import PeriodoController
from modules.asignaciones.presentation.controllers.participacion_usuario_controller import ParticipacionUsuarioController
from modules.asignaciones.presentation.controllers.respuesta_controller import RespuestaController
from modules.consultas.presentation.controllers.consulta_controller import ConsultaController
from modules.conversaciones.presentation.controllers.conversacion_controller import (
    ConversacionController,
)
from modules.conversaciones.presentation.controllers.solicitud_comentario_controller import (
    SolicitudComentarioController,
)

import os

api_version = "2.0.0"
api_namespace = "api"

if os.environ.get("PYTEST_CURRENT_TEST"):
    import sys
    from ninja.errors import ConfigError
    import uuid

    if hasattr(sys, "_ninja_api_instance"):
        api = sys._ninja_api_instance
    else:
        try:
            api = NinjaExtraAPI(
                title="Generic API (Test)",
                version=api_version,
                urls_namespace="api-test-suite",
                description="Generic API Boilerplate",
                auth=JWTAuth(),
                docs_url="/docs",
            )
        except ConfigError:
            api = NinjaExtraAPI(
                title="Generic API (Test)",
                version=api_version,
                urls_namespace=f"api-test-{uuid.uuid4().hex[:6]}",
                description="Generic API Boilerplate",
                auth=JWTAuth(),
                docs_url="/docs",
            )
        sys._ninja_api_instance = api
else:
    api = NinjaExtraAPI(
        title="Generic API",
        version=api_version,
        urls_namespace=api_namespace,
        description="Generic API Boilerplate",
        auth=JWTAuth(),
        docs_url="/docs",
    )

# ── Controllers JWT (token/pair, token/refresh, token/verify) ─
api.register_controllers(NinjaJWTDefaultController)

# ── Auth Controllers (modular login by username/dni/email) ─
api.register_controllers(AuthLoginController)
api.register_controllers(AuthMeController)

# ── Usuarios Controllers ─
api.register_controllers(AreaController)
api.register_controllers(UsuarioMencionableController)

# ── Ingeniero Habilitado Controllers ─
api.register_controllers(IngenieroHabilitadoController)

# ── Tramites Controllers ─
api.register_controllers(ExpedienteController)
api.register_controllers(SolicitudController)
api.register_controllers(TipoDocumentoController)

# ── Asignaciones Controllers ─
api.register_controllers(NotificacionController)
api.register_controllers(PeriodoController)
api.register_controllers(ParticipacionUsuarioController)
api.register_controllers(RespuestaController)

# ── Consultas Controllers ─
api.register_controllers(ConsultaController)

# ── Conversaciones Controllers ─
api.register_controllers(ConversacionController)
api.register_controllers(SolicitudComentarioController)

# ── Exception handlers globales ────────────────────────────────
register_exception_handlers(api)