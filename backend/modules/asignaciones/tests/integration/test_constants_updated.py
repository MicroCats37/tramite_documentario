"""
Tests para las constantes del módulo asignaciones — particularmente los nuevos
estados operativos del período y tipos de cierre.
"""
import pytest

from modules.asignaciones.domain.constants import (
    TipoParticipacion,
    EstadoPeriodo,
    TipoCierre,
    EstadoPeriodoOperativo,
    OrigenEstadoPeriodo,
)


class TestEstadoPeriodoOperativo:
    """Tests para el nuevo EstadoPeriodoOperativo."""

    def test_estados_definidos(self):
        """Verifica que los tres estados operativos están definidos."""
        assert EstadoPeriodoOperativo.PENDIENTE == "PENDIENTE"
        assert EstadoPeriodoOperativo.EN_GESTION == "EN_GESTION"
        assert EstadoPeriodoOperativo.CERRADO == "CERRADO"

    def test_no_tiene_respondida(self):
        """Verifica que RESPONDIDA NO es un estado del período."""
        choices_values = [choice[0] for choice in EstadoPeriodoOperativo.choices]
        assert "RESPONDIDA" not in choices_values

    def test_no_tiene_recibida(self):
        """Verifica que RECIBIDA NO es un estado del período (salvo acción institucional explícita)."""
        choices_values = [choice[0] for choice in EstadoPeriodoOperativo.choices]
        assert "RECIBIDA" not in choices_values

    def test_choices_tienen_label(self):
        """Verifica que todos los estados tienen label legible."""
        for choice in EstadoPeriodoOperativo.choices:
            assert len(choice) == 2
            assert choice[1]  # label no vacío


class TestOrigenEstadoPeriodo:
    """Tests para el nuevo OrigenEstadoPeriodo."""

    def test_origenes_principales_definidos(self):
        """Verifica que los orígenes principales están definidos."""
        assert OrigenEstadoPeriodo.CREACION == "CREACION"
        assert OrigenEstadoPeriodo.AUTOASIGNACION == "AUTOASIGNACION"
        assert OrigenEstadoPeriodo.CIERRE == "CIERRE"

    def test_origenes_para_cierres_especiales(self):
        """Verifica que existen orígenes para cierres especiales."""
        assert OrigenEstadoPeriodo.CAMBIO_PARTICIPACION == "CAMBIO_PARTICIPACION"
        assert OrigenEstadoPeriodo.ASIGNACION_ERRONEA == "ASIGNACION_ERRONEA"


class TestTipoCierreActualizado:
    """Tests para los tipos de cierre — verifica adiciones."""

    def test_asignacion_erronea_presente(self):
        """Verifica que ASIGNACION_ERRONEA está en TipoCierre."""
        choices_values = [choice[0] for choice in TipoCierre.choices]
        assert "ASIGNACION_ERRONEA" in choices_values

    def test_cambio_participacion_presente(self):
        """Verifica que CAMBIO_PARTICIPACION está en TipoCierre."""
        choices_values = [choice[0] for choice in TipoCierre.choices]
        assert "CAMBIO_PARTICIPACION" in choices_values

    def test_tipos_cierre_originales_presentes(self):
        """Verifica que los tipos de cierre originales siguen presentes."""
        originales = [
            "FINALIZADO",
            "DERIVADO",
            "RETIRADO",
            "RECHAZADO",
            "ANULADO",
        ]
        choices_values = [choice[0] for choice in TipoCierre.choices]
        for tipo in originales:
            assert tipo in choices_values

    def test_relacion_entre_origen_y_tipo_cierre(self):
        """Verifica que existe coherencia entre origen de transición y tipo de cierre.

        El origen indica qué acción disparó la transición;
        tipo_cierre indica cómo terminó el período.
        Son campos relacionados pero distintos.
        """
        # Un cambio de participación tiene origen específico
        assert (
            OrigenEstadoPeriodo.CAMBIO_PARTICIPACION
            == "CAMBIO_PARTICIPACION"
        )
        # Y también existe como tipo de cierre
        assert (
            TipoCierre.CAMBIO_PARTICIPACION
            == "CAMBIO_PARTICIPACION"
        )

        # Una asignación errónea tiene origen específico
        assert (
            OrigenEstadoPeriodo.ASIGNACION_ERRONEA
            == "ASIGNACION_ERRONEA"
        )


class TestEstadoPeriodo:
    """Tests para el estado del período — PENDIENTE/EN_GESTION/CERRADO."""

    def test_estados_definidos(self):
        """Verifica que los tres estados están definidos."""
        assert EstadoPeriodo.PENDIENTE == "PENDIENTE"
        assert EstadoPeriodo.EN_GESTION == "EN_GESTION"
        assert EstadoPeriodo.CERRADO == "CERRADO"

    def test_no_tiene_abierto(self):
        """Verifica que ABIERTO ya NO es un estado del período."""
        choices_values = [choice[0] for choice in EstadoPeriodo.choices]
        assert "ABIERTO" not in choices_values

    def test_choices_tienen_label(self):
        """Verifica que todos los estados tienen label legible."""
        for choice in EstadoPeriodo.choices:
            assert len(choice) == 2
            assert choice[1]



    """Tests para verificar que estado y tipo_cierre son independientes."""

    def test_estado_periodo_y_tipo_cierre_son_diferentes_enums(self):
        """Verifica que EstadoPeriodoOperativo y TipoCierre son enums separados."""
        # EstadoPeriodoOperativo tiene: PENDIENTE, EN_GESTION, CERRADO
        operativo_values = [c[0] for c in EstadoPeriodoOperativo.choices]
        assert "PENDIENTE" in operativo_values
        assert "CERRADO" in operativo_values

        # TipoCierre NO debe tener estados operativos
        cierre_values = [c[0] for c in TipoCierre.choices]
        assert "PENDIENTE" not in cierre_values
        assert "EN_GESTION" not in cierre_values
        # Pero SÍ debe tener valores de cierre
        assert "FINALIZADO" in cierre_values
        assert "ASIGNACION_ERRONEA" in cierre_values
