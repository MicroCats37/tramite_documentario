"""
AuthMeController — endpoint HTTP para obtener el usuario autenticado actual.

Delgado: solo lee request.auth y retorna los datos del usuario vía presenter.
"""
from uuid import UUID

from injector import inject
from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated

from core.responses import ApiResponse, success_response
from modules.usuarios.presentation.schemas.auth_schemas import AuthUserOut
from modules.usuarios.presentation.presenters.auth_presenter import AuthPresenter


@api_controller("/auth", tags=["Autenticación"], permissions=[IsAuthenticated])
class AuthMeController:
    """
    Controlador para obtener el usuario autenticado actual.

    Lee el usuario del JWT (request.auth) y retorna sus datos con áreas asignadas vigentes.
    """

    @inject
    def __init__(self, auth_presenter: AuthPresenter):
        self.auth_presenter = auth_presenter

    @route.get("/me/", response={200: ApiResponse[AuthUserOut]})
    async def get_me(self, request):
        """
        Obtiene los datos del usuario autenticado actualmente.

        El usuario se extrae del JWT presente en el request (request.auth).
        Retorna: datos del usuario y áreas asignadas vigentes.
        """
        from modules.usuarios.domain.services.core.auth_core_service import AuthCoreService

        user = request.auth  # JWTAuth decodifica el token y adjunta el usuario

        # Build user result with active areas using the service
        auth_service = AuthCoreService()
        user_result = await auth_service.build_user_result(user)

        # Return using the nested structure (AuthUserOut with datos + areas_asignadas_vigentes)
        return success_response(AuthUserOut(
            datos=user_result.datos,
            areas_asignadas_vigentes=user_result.areas_asignadas_vigentes,
        ))
