"""
Tests para SolicitudAsignacionPeriodoEstadoHistorial — modelo e inicial/historial.
"""
import pytest
from datetime import datetime, timezone

from modules.asignaciones.domain.constants import (
    EstadoPeriodoOperativo,
    OrigenEstadoPeriodo,
    TipoCierre,
)
from modules.asignaciones.domain.models import (
    SolicitudAsignacion,
    SolicitudAsignacionPeriodo,
    SolicitudAsignacionPeriodoEstadoHistorial,
)


pytestmark = pytest.mark.django_db


# ── Helpers ────────────────────────────────────────────────────────────────────

def crear_periodo_con_historial_inicial(usuario=None):
    """Crea Solicitud, Asignación, Período y historial inicial PENDIENTE."""
    from modules.tramites.domain.models import Solicitud, Expediente
    from modules.usuarios.domain.models import Area
    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = usuario or User.objects.create_user(username="testuser", password="test", dni="12345678")

    # Crear expediente mínimo
    expediente = Expediente.objects.create(
        numero=1,
        razon_social="Test SAC",
        ruc="12345678901",
        tipo_documento="RUC",
        numero_documento="12345678901",
        asunto="Asunto de prueba",
        creado_por=user,
        fecha_registro=datetime.now(timezone.utc),
    )

    # Crear solicitud
    solicitud = Solicitud.objects.create(
        expediente=expediente,
        prioridad="MEDIA",
        fecha_registro=datetime.now(timezone.utc),
        creado_por=user,
    )

    # Crear área
    area = Area.objects.create(
        nombre="Área de Prueba",
        activo=True,
    )

    # Crear asignación
    asignacion = SolicitudAsignacion.objects.create(
        solicitud=solicitud,
        area=area,
        fecha_incorporacion=datetime.now(timezone.utc),
        incorporado_por=user,
    )

    # Crear período
    fecha_inicio = datetime.now(timezone.utc)
    periodo = SolicitudAsignacionPeriodo.objects.create(
        asignacion=asignacion,
        numero_ciclo=1,
        tipo_participacion="PRINCIPAL",
        estado="PENDIENTE",
        fecha_inicio=fecha_inicio,
        iniciado_por=user,
    )

    return {
        "user": user,
        "expediente": expediente,
        "solicitud": solicitud,
        "area": area,
        "asignacion": asignacion,
        "periodo": periodo,
        "fecha_inicio": fecha_inicio,
    }


# ── Model Tests ────────────────────────────────────────────────────────────────

class TestSolicitudAsignacionPeriodoEstadoHistorialModel:
    """Tests para el modelo de historial de estado del período."""

    def test_crear_historial_inicial_genera_registro_correcto(self):
        """
        GIVEN: Un período recién creado
        WHEN: Se crea un historial inicial con estado PENDIENTE
        THEN: El registro tiene estado_anterior NULL, estado_nuevo PENDIENTE, origen CREACION
        """
        data = crear_periodo_con_historial_inicial()
        periodo = data["periodo"]
        fecha_inicio = data["fecha_inicio"]

        historial = SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
            periodo=periodo,
            estado_anterior=None,
            estado_nuevo=EstadoPeriodoOperativo.PENDIENTE,
            fecha_cambio=fecha_inicio,
            cambiado_por=data["user"],
            origen=OrigenEstadoPeriodo.CREACION,
        )

        assert historial.periodo == periodo
        assert historial.estado_anterior is None
        assert historial.estado_nuevo == EstadoPeriodoOperativo.PENDIENTE
        assert historial.fecha_cambio == fecha_inicio
        assert historial.cambiado_por == data["user"]
        assert historial.origen == OrigenEstadoPeriodo.CREACION
        assert historial.motivo is None

    def test_crear_transicion_pENDIENTE_a_EN_GESTION(self):
        """
        GIVEN: Un período con historial PENDIENTE
        WHEN: Se registra transición a EN_GESTION
        THEN: El registro tiene estado_anterior PENDIENTE, estado_nuevo EN_GESTION
        """
        data = crear_periodo_con_historial_inicial()
        periodo = data["periodo"]

        fecha_transicion = datetime.now(timezone.utc)
        historial = SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
            periodo=periodo,
            estado_anterior=EstadoPeriodoOperativo.PENDIENTE,
            estado_nuevo=EstadoPeriodoOperativo.EN_GESTION,
            fecha_cambio=fecha_transicion,
            cambiado_por=data["user"],
            origen=OrigenEstadoPeriodo.AUTOASIGNACION,
        )

        assert historial.estado_anterior == EstadoPeriodoOperativo.PENDIENTE
        assert historial.estado_nuevo == EstadoPeriodoOperativo.EN_GESTION
        assert historial.origen == OrigenEstadoPeriodo.AUTOASIGNACION

    def test_crear_transicion_EN_GESTION_a_CERRADO(self):
        """
        GIVEN: Un período con historial EN_GESTION
        WHEN: Se registra transición a CERRADO
        THEN: El registro tiene estado_anterior EN_GESTION, estado_nuevo CERRADO
        """
        data = crear_periodo_con_historial_inicial()
        periodo = data["periodo"]

        # Primera transición: PENDIENTE -> EN_GESTION
        SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
            periodo=periodo,
            estado_anterior=None,
            estado_nuevo=EstadoPeriodoOperativo.PENDIENTE,
            fecha_cambio=data["fecha_inicio"],
            cambiado_por=data["user"],
            origen=OrigenEstadoPeriodo.CREACION,
        )

        # Segunda transición: EN_GESTION -> CERRADO
        fecha_cierre = datetime.now(timezone.utc)
        historial = SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
            periodo=periodo,
            estado_anterior=EstadoPeriodoOperativo.EN_GESTION,
            estado_nuevo=EstadoPeriodoOperativo.CERRADO,
            fecha_cambio=fecha_cierre,
            cambiado_por=data["user"],
            origen=OrigenEstadoPeriodo.CIERRE,
            motivo="Trabajo completado",
        )

        assert historial.estado_anterior == EstadoPeriodoOperativo.EN_GESTION
        assert historial.estado_nuevo == EstadoPeriodoOperativo.CERRADO
        assert historial.origen == OrigenEstadoPeriodo.CIERRE
        assert historial.motivo == "Trabajo completado"

    def test_str_representacion_correcta(self):
        """
        GIVEN: Un historial con estados definidos
        WHEN: Se obtiene su __str__
        THEN: La representación es "{periodo} — {anterior} → {nuevo}"
        """
        data = crear_periodo_con_historial_inicial()
        periodo = data["periodo"]

        historial = SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
            periodo=periodo,
            estado_anterior=EstadoPeriodoOperativo.PENDIENTE,
            estado_nuevo=EstadoPeriodoOperativo.EN_GESTION,
            fecha_cambio=datetime.now(timezone.utc),
            cambiado_por=data["user"],
        )

        str_repr = str(historial)
        assert "PENDIENTE" in str_repr
        assert "EN_GESTION" in str_repr

    def test_str_con_estado_inicial_muestra_flecha_desde_nulo(self):
        """
        GIVEN: Un historial inicial (estado_anterior=None)
        WHEN: Se obtiene su __str__
        THEN: Muestra "∅" como estado anterior
        """
        data = crear_periodo_con_historial_inicial()
        periodo = data["periodo"]

        historial = SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
            periodo=periodo,
            estado_anterior=None,
            estado_nuevo=EstadoPeriodoOperativo.PENDIENTE,
            fecha_cambio=datetime.now(timezone.utc),
            cambiado_por=data["user"],
            origen=OrigenEstadoPeriodo.CREACION,
        )

        str_repr = str(historial)
        assert "∅" in str_repr
        assert "PENDIENTE" in str_repr

    def test_relacion_inversa_periodo_historial(self):
        """
        GIVEN: Un período con múltiples registros de historial
        WHEN: Se accede a historial_estados desde el período
        THEN: Los registros están ordenados por fecha_cambio
        """
        data = crear_periodo_con_historial_inicial()
        periodo = data["periodo"]
        user = data["user"]

        # Crear varios registros
        h1 = SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
            periodo=periodo,
            estado_anterior=None,
            estado_nuevo=EstadoPeriodoOperativo.PENDIENTE,
            fecha_cambio=data["fecha_inicio"],
            cambiado_por=user,
            origen=OrigenEstadoPeriodo.CREACION,
        )

        h2 = SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
            periodo=periodo,
            estado_anterior=EstadoPeriodoOperativo.PENDIENTE,
            estado_nuevo=EstadoPeriodoOperativo.EN_GESTION,
            fecha_cambio=datetime.now(timezone.utc),
            cambiado_por=user,
            origen=OrigenEstadoPeriodo.AUTOASIGNACION,
        )

        h3 = SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
            periodo=periodo,
            estado_anterior=EstadoPeriodoOperativo.EN_GESTION,
            estado_nuevo=EstadoPeriodoOperativo.CERRADO,
            fecha_cambio=datetime.now(timezone.utc),
            cambiado_por=user,
            origen=OrigenEstadoPeriodo.CIERRE,
        )

        # Verificar ordenamiento
        historial_list = list(periodo.historial_estados.all())
        assert historial_list[0].estado_nuevo == EstadoPeriodoOperativo.PENDIENTE
        assert historial_list[1].estado_nuevo == EstadoPeriodoOperativo.EN_GESTION
        assert historial_list[2].estado_nuevo == EstadoPeriodoOperativo.CERRADO

    def test_cambiado_por_opcional_para_sistema_legacy(self):
        """
        GIVEN: Un registro de historial sin usuario (Legacy)
        WHEN: Se crea sin cambiado_por
        THEN: El registro se crea correctamente con cambiado_por=NULL
        """
        data = crear_periodo_con_historial_inicial()
        periodo = data["periodo"]

        historial = SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
            periodo=periodo,
            estado_anterior=None,
            estado_nuevo=EstadoPeriodoOperativo.PENDIENTE,
            fecha_cambio=datetime.now(timezone.utc),
            cambiado_por=None,
            origen=OrigenEstadoPeriodo.CREACION,
        )

        assert historial.cambiado_por is None


# ── Constraints Tests ─────────────────────────────────────────────────────────

class TestPeriodoEstadoHistorialConstraints:
    """Tests para restricciones del historial de estados."""

    def test_multiple_transiciones_ordenadas_por_fecha(self):
        """
        GIVEN: Un período con transiciones a diferentes horas
        WHEN: Se consultan los registros
        THEN: Aparecen en orden cronológico
        """
        data = crear_periodo_con_historial_inicial()
        periodo = data["periodo"]
        user = data["user"]

        from datetime import timedelta

        base = data["fecha_inicio"]

        # Transición 1: PENDIENTE
        h1 = SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
            periodo=periodo,
            estado_anterior=None,
            estado_nuevo=EstadoPeriodoOperativo.PENDIENTE,
            fecha_cambio=base,
            cambiado_por=user,
            origen=OrigenEstadoPeriodo.CREACION,
        )

        # Transición 2: EN_GESTION (1 hora después)
        h2 = SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
            periodo=periodo,
            estado_anterior=EstadoPeriodoOperativo.PENDIENTE,
            estado_nuevo=EstadoPeriodoOperativo.EN_GESTION,
            fecha_cambio=base + timedelta(hours=1),
            cambiado_por=user,
            origen=OrigenEstadoPeriodo.AUTOASIGNACION,
        )

        # Transición 3: CERRADO (3 horas después)
        h3 = SolicitudAsignacionPeriodoEstadoHistorial.objects.create(
            periodo=periodo,
            estado_anterior=EstadoPeriodoOperativo.EN_GESTION,
            estado_nuevo=EstadoPeriodoOperativo.CERRADO,
            fecha_cambio=base + timedelta(hours=3),
            cambiado_por=user,
            origen=OrigenEstadoPeriodo.CIERRE,
        )

        historial_list = list(periodo.historial_estados.all())

        assert len(historial_list) == 3
        assert historial_list[0].estado_nuevo == EstadoPeriodoOperativo.PENDIENTE
        assert historial_list[1].estado_nuevo == EstadoPeriodoOperativo.EN_GESTION
        assert historial_list[2].estado_nuevo == EstadoPeriodoOperativo.CERRADO


# ── Service Tests ─────────────────────────────────────────────────────────────

class TestPeriodoEstadoHistorialCoreService:
    """Tests para el servicio de historial de estados."""

    def test_crear_historial_inicial_con_service(self):
        """
        GIVEN: Un período recién creado
        WHEN: Se usa crear_historial_inicial del servicio
        THEN: Crea el registro PENDIENTE con origen CREACION
        """
        from modules.asignaciones.domain.services.core import PeriodoEstadoHistorialCoreService

        data = crear_periodo_con_historial_inicial()
        periodo = data["periodo"]
        service = PeriodoEstadoHistorialCoreService()

        historial = service.crear_historial_inicial(
            periodo=periodo,
            fecha_inicio=data["fecha_inicio"],
            iniciado_por=data["user"],
        )

        assert historial.estado_anterior is None
        assert historial.estado_nuevo == EstadoPeriodoOperativo.PENDIENTE
        assert historial.origen == OrigenEstadoPeriodo.CREACION
        assert historial.fecha_cambio == data["fecha_inicio"]
        assert historial.cambiado_por == data["user"]

    def test_registrar_transicion_simple(self):
        """
        GIVEN: Un período con historial PENDIENTE
        WHEN: Se usa registrar_transicion para cambiar a EN_GESTION
        THEN: Crea el registro con estados correctos
        """
        from modules.asignaciones.domain.services.core import PeriodoEstadoHistorialCoreService

        data = crear_periodo_con_historial_inicial()
        periodo = data["periodo"]
        service = PeriodoEstadoHistorialCoreService()

        # Crear inicial primero
        service.crear_historial_inicial(
            periodo=periodo,
            fecha_inicio=data["fecha_inicio"],
            iniciado_por=data["user"],
        )

        # Registrar transición
        fecha_trans = datetime.now(timezone.utc)
        historial = service.registrar_transicion(
            periodo=periodo,
            estado_anterior=EstadoPeriodoOperativo.PENDIENTE,
            estado_nuevo=EstadoPeriodoOperativo.EN_GESTION,
            fecha_cambio=fecha_trans,
            cambiado_por=data["user"],
            origen=OrigenEstadoPeriodo.AUTOASIGNACION,
            motivo="Usuario se autoasignó",
        )

        assert historial.estado_anterior == EstadoPeriodoOperativo.PENDIENTE
        assert historial.estado_nuevo == EstadoPeriodoOperativo.EN_GESTION
        assert historial.origen == OrigenEstadoPeriodo.AUTOASIGNACION
        assert historial.motivo == "Usuario se autoasignó"

    def test_registrar_transicion_para_cierre(self):
        """
        GIVEN: Un período con historial EN_GESTION
        WHEN: Se usa registrar_transicion para cerrar con tipo_cierre
        THEN: Crea el registro con origen CIERRE
        """
        from modules.asignaciones.domain.services.core import PeriodoEstadoHistorialCoreService

        data = crear_periodo_con_historial_inicial()
        periodo = data["periodo"]
        service = PeriodoEstadoHistorialCoreService()

        # Crear inicial y transición a EN_GESTION
        service.crear_historial_inicial(
            periodo=periodo,
            fecha_inicio=data["fecha_inicio"],
            iniciado_por=data["user"],
        )

        service.registrar_transicion(
            periodo=periodo,
            estado_anterior=EstadoPeriodoOperativo.PENDIENTE,
            estado_nuevo=EstadoPeriodoOperativo.EN_GESTION,
            fecha_cambio=datetime.now(timezone.utc),
            cambiado_por=data["user"],
            origen=OrigenEstadoPeriodo.AUTOASIGNACION,
        )

        # Registrar cierre
        historial = service.registrar_transicion(
            periodo=periodo,
            estado_anterior=EstadoPeriodoOperativo.EN_GESTION,
            estado_nuevo=EstadoPeriodoOperativo.CERRADO,
            fecha_cambio=datetime.now(timezone.utc),
            cambiado_por=data["user"],
            origen=OrigenEstadoPeriodo.CIERRE,
            motivo="Finalizado correctamente",
        )

        assert historial.estado_anterior == EstadoPeriodoOperativo.EN_GESTION
        assert historial.estado_nuevo == EstadoPeriodoOperativo.CERRADO
        assert historial.origen == OrigenEstadoPeriodo.CIERRE

    def test_fecha_cambio_puede_ser_histrica(self):
        """
        GIVEN: Un período
        WHEN: Se registra una transición con fecha del pasado
        THEN: El registro conserva la fecha histórica correcta
        """
        from modules.asignaciones.domain.services.core import PeriodoEstadoHistorialCoreService
        from datetime import timedelta

        data = crear_periodo_con_historial_inicial()
        periodo = data["periodo"]
        service = PeriodoEstadoHistorialCoreService()

        fecha_historica = data["fecha_inicio"] - timedelta(days=5)

        historial = service.registrar_transicion(
            periodo=periodo,
            estado_anterior=None,
            estado_nuevo=EstadoPeriodoOperativo.PENDIENTE,
            fecha_cambio=fecha_historica,
            cambiado_por=data["user"],
            origen=OrigenEstadoPeriodo.CREACION,
        )

        assert historial.fecha_cambio == fecha_historica
        assert historial.fecha_cambio < datetime.now(timezone.utc)
