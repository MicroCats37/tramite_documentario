"""
AuthPresenter — transforma LoginTokenResult a esquema HTTP LoginTokenOut.
"""
from modules.usuarios.presentation.schemas.auth_schemas import (
    AreaAsignadaOut,
    AuthUserOut,
    LoginTokenOut,
    UserDatosOut,
)


class AuthPresenter:
    """
    Transforma objetos de resultado del dominio a esquemas de respuesta HTTP.
    Desacopla el formateo de respuesta de los controladores.
    """

    @staticmethod
    def present_login(result) -> LoginTokenOut:
        """
        Transforma un LoginTokenResult a LoginTokenOut.

        Args:
            result: LoginTokenResult del servicio de dominio

        Returns:
            Esquema LoginTokenOut listo para respuesta HTTP
        """
        return LoginTokenOut(
            access_token=result.access_token,
            refresh_token=result.refresh_token,
            expires_at=result.expires_at,
            user=AuthUserOut(
                datos=UserDatosOut(
                    id=result.user.datos.id,
                    username=result.user.datos.username,
                    dni=result.user.datos.dni,
                    email=result.user.datos.email,
                    nombres=result.user.datos.nombres,
                    apellidos=result.user.datos.apellidos,
                    is_staff=result.user.datos.is_staff,
                    is_superuser=result.user.datos.is_superuser,
                ),
                areas_asignadas_vigentes=[
                    AreaAsignadaOut(
                        id=area.id,
                        area_id=area.area_id,
                        area_nombre=area.area_nombre,
                        cargo_id=area.cargo_id,
                        cargo_nombre=area.cargo_nombre,
                    )
                    for area in result.user.areas_asignadas_vigentes
                ],
            ),
        )
