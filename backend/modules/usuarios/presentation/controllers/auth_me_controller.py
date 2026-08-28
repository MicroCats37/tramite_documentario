"""
AuthMeController — endpoint HTTP para obtener el usuario autenticado actual.

Delgado: solo lee request.auth y retorna los datos del usuario vía presenter.
"""
from uuid import UUID

from ninja_extra import api_controller, route
from ninja_extra.permissions import IsAuthenticated

from core.responses import ApiResponse, success_response
from modules.usuarios.presentation.schemas.auth_schemas import AuthUserOut


@api_controller("/auth", tags=["Autenticación"], permissions=[IsAuthenticated])
class AuthMeController:
    """
    Controlador para obtener el usuario autenticado actual.

    Lee el usuario del JWT (request.auth) y retorna sus datos.
    """

    @route.get("/me/", response={200: ApiResponse[AuthUserOut]})
    async def get_me(self, request):
        """
        Obtiene los datos del usuario autenticado actualmente.

        El usuario se extrae del JWT presente en el request (request.auth).
        Retorna: id, username, dni, email, nombres, apellidos, is_staff, is_superuser.
        """
        user = request.auth  # JWTAuth decodifica el token y adjunta el usuario

        return success_response(AuthUserOut(
            id=user.id,
            username=user.username,
            dni=getattr(user, "dni", None),
            email=getattr(user, "email", None),
            nombres=getattr(user, "nombres", None),
            apellidos=getattr(user, "apellidos", None),
            is_staff=user.is_staff,
            is_superuser=user.is_superuser,
        ))
