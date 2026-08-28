Sí. Con tu necesidad de medir tiempos por estado, yo sí crearía la tabla de historial de estados del período. Ahí deja de ser sobreingeniería: tienes un requerimiento analítico concreto.

Tu SolicitudAsignacionPeriodo ya es precisamente la entidad que representa cada ciclo de un área dentro de la solicitud. Yo haría que guarde el estado actual, y una tabla hija guarde todas las transiciones.

1. SolicitudAsignacionPeriodo

Quedaría conceptualmente así:

Campo	Función
asignacion	Solicitud + Área
numero_ciclo	1, 2, 3...
tipo_participacion	PRINCIPAL / ADJUNTA
estado	Estado operativo actual
fecha_inicio	Inicio real del ciclo
fecha_fin	Fin real del ciclo
tipo_cierre	Cómo terminó
iniciado_por	Actor inicial
finalizado_por	Actor de cierre
motivo_cierre	Motivo
observacion	Opcional

El campo:

estado

sirve para consultas rápidas:

¿Cuáles están pendientes?
¿Cuáles están recibidas?
¿Cuáles están en gestión?

sin reconstruir todo el historial cada vez.

2. Nueva tabla SolicitudAsignacionPeriodoEstadoHistorial

Yo sí la añadiría.

Campo	Función
periodo	Período al que pertenece
estado_anterior	Estado previo, nullable para el inicial
estado_nuevo	Estado al que pasó
fecha_cambio	Fecha real del cambio
cambiado_por	Usuario que ejecutó la transición; nullable para sistema/Legacy
motivo	Opcional
origen	Opcional: CREACION, RECEPCION, AUTOASIGNACION, CIERRE, etc.

Y obviamente hereda:

id
created_at
updated_at

del BaseModel.

Importantísimo para Legacy

fecha_cambio no debería ser auto_now_add.

Puedes cargar hoy:

fecha_cambio = 2023-04-10
created_at   = 2026-08-27

y conservar correctamente las métricas históricas.

3. Estados que usaría inicialmente

Yo empezaría pequeño:

PENDIENTE
RECIBIDA
EN_GESTION
CERRADA
PENDIENTE

El área ya tiene un período creado, pero todavía no ha reconocido/recibido formalmente la intervención.

RECIBIDA

El área ya reconoce la recepción.

Esto debe corresponder a una acción real de negocio. No a que Juan simplemente haya visto la notificación.

La vista individual sigue viviendo en:

NotificacionUsuario.vista_at
EN_GESTION

El área ya comenzó a trabajar formalmente.

Puede dispararse, por ejemplo, al autoasignarse el primer usuario, si esa es la regla que eliges.

CERRADA

Ese período terminó.

Y ahí:

tipo_cierre

explica por qué:

FINALIZADO
DERIVADO
RETIRADO
RECHAZADO
ANULADO
ASIGNACION_ERRONEA
CAMBIO_PARTICIPACION
4. Cómo se registra

Al crear el período:

SolicitudAsignacionPeriodo
estado = PENDIENTE
fecha_inicio = 08:00

y simultáneamente:

PeriodoEstadoHistorial

estado_anterior = NULL
estado_nuevo    = PENDIENTE
fecha_cambio    = 08:00

Después el área recibe:

Periodo.estado
PENDIENTE → RECIBIDA

y agregas:

Historial

estado_anterior = PENDIENTE
estado_nuevo    = RECIBIDA
fecha_cambio    = 08:17

Empieza gestión:

RECIBIDA → EN_GESTION

Historial:

08:25

Termina:

EN_GESTION → CERRADA

y además:

Periodo.fecha_fin   = 11:40
Periodo.tipo_cierre = FINALIZADO
5. Así sacas exactamente los tiempos que necesitas

Tendrías:

08:00 PENDIENTE
08:17 RECIBIDA
08:25 EN_GESTION
11:40 CERRADA

Entonces:

Tiempo pendiente
= 17 min
Tiempo recibida pero sin gestión
= 8 min
Tiempo en gestión
= 3 h 15 min
Tiempo total del período
= 3 h 40 min

Eso sí es información operativa de muchísimo valor.

6. Y no necesitas guardar fecha_recepcion, fecha_inicio_gestion, etc.

Esta es otra ventaja.

Antes te sugerí campos como:

fecha_recepcion
fecha_inicio_gestion

Pero si ya creamos historial de estados, yo no los pondría.

Porque terminarías duplicando:

Periodo.fecha_recepcion = 08:17

y:

Historial RECIBIDA = 08:17

Dos fuentes de verdad.

Con el historial:

fecha de recepción
= fecha de transición a RECIBIDA

y listo.

7. El estado actual sigue siendo útil

Podrías preguntarte:

Si tengo todo el historial, ¿por qué guardar Periodo.estado?

Porque para operación diaria quieres hacer:

dame todos los períodos EN_GESTION

y no:

dame la última fila de historial de cada período y averigua cuál es su último estado.

Entonces:

Periodo.estado
= snapshot actual
PeriodoEstadoHistorial
= película completa

Es el mismo patrón que ya estamos usando con:

Solicitud.estado
+
SolicitudEstadoHistorial

De hecho, arquitectónicamente queda muy consistente.

8. Única regla importante

Nunca permitir:

periodo.estado = EN_GESTION

por un PATCH arbitrario.

Debería pasar por algo como:

cambiar_estado_periodo(...)

que dentro de una transacción haga:

1. validar transición
2. actualizar Periodo.estado
3. crear PeriodoEstadoHistorial
4. si pasa a CERRADA:
      completar fecha_fin
      completar tipo_cierre

Así las dos fuentes nunca se separan.

9. Transiciones permitidas inicialmente

Yo las mantendría simples:

PENDIENTE
   ↓
RECIBIDA
   ↓
EN_GESTION
   ↓
CERRADA

Pero permitiría cierres anticipados:

PENDIENTE → CERRADA

por ejemplo:

ASIGNACION_ERRONEA
ANULADO

y:

RECIBIDA → CERRADA

por:

RETIRADO
RECHAZADO
DERIVADO

según negocio.

No asumiría que todas tienen que recorrer obligatoriamente los cuatro estados.

Entonces sí: esta es la estructura que recomiendo
SolicitudAsignacion
        │
        └── SolicitudAsignacionPeriodo
                    │
                    │ estado ACTUAL
                    │
                    ├── SolicitudAsignacionPeriodoEstadoHistorial
                    │       ├── PENDIENTE 08:00
                    │       ├── RECIBIDA 08:17
                    │       ├── EN_GESTION 08:25
                    │       └── CERRADA 11:40
                    │
                    └── SolicitudAsignacionUsuario

Para tu sistema, yo sí añadiría esa tabla. Te da exactamente la trazabilidad temporal por área que necesitas para métricas, sin llenar Periodo de cuatro o cinco columnas de fecha específicas.