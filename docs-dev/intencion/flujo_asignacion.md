# Flujo Operativo V2 — Expedientes, Solicitudes y Asignaciones por Área

> Documento funcional para orientar la implementación de endpoints y servicios de dominio.
>
> El objetivo no es diseñar un CRUD por cada tabla, sino definir **operaciones de negocio completas** que puedan modificar varias tablas dentro de una misma transacción.

---

# 1. Alcance

Este documento cubre el flujo operativo desde:

```text
Ingreso de Expediente
        ↓
Creación de Solicitud
        ↓
Distribución inicial a áreas
        ↓
Operación de las áreas
        ↓
Autoasignación / participación de usuarios
        ↓
Cambios de participación
        ↓
Derivaciones / devoluciones
        ↓
Finalización de períodos
        ↓
Punto de salida hacia la siguiente etapa del trámite
```

Por ahora quedan **fuera de alcance**:

- permisos finos por cargo o grupo;
- autorización específica por acción;
- firma;
- respuesta institucional final;
- consolidación documental final;
- liquidación/pago definitivo;
- reglas finales de cierre institucional.

En esta primera etapa, los endpoints podrán exigir únicamente que el usuario esté autenticado.

La autorización detallada puede añadirse después sin modificar el núcleo del flujo.

---

# 2. Principio general del diseño

La arquitectura separa cuatro conceptos:

```text
Solicitud
= trámite global

SolicitudAsignacion
= relación estable Solicitud ↔ Área

SolicitudAsignacionPeriodo
= cada participación temporal concreta del área

SolicitudAsignacionUsuario
= personas que trabajan por esa área durante ese período
```

La estructura base es:

```text
Solicitud
   │
   ├── SolicitudEstadoHistorial
   │
   └── SolicitudAsignacion
            │
            └── SolicitudAsignacionPeriodo
                     │
                     ├── SolicitudAsignacionUsuario
                     └── SolicitudDerivacion
```

Las notificaciones se encuentran alrededor del flujo:

```text
Notificacion
   │
   └── NotificacionUsuario
```

La parte de `SolicitudAsignacionRespuesta` se deja prevista en el modelo, pero **no forma parte todavía del flujo operativo detallado de esta versión**.

---

# 3. Principio de API: acciones de negocio, no CRUD de tablas

No se recomienda que el frontend construya manualmente operaciones administrativas mediante llamadas independientes como:

```text
PATCH período origen
POST asignación destino
POST período destino
POST derivación
POST notificación
```

Una operación como `DERIVAR` representa un único hecho de negocio y debe ejecutarse mediante un servicio transaccional del backend.

Ejemplo recomendado:

```http
POST /api/periodos/{id}/derivar
```

El backend se encarga internamente de:

1. validar el período origen;
2. cerrar el período origen;
3. localizar o crear la asignación del área destino;
4. localizar o abrir el período destino;
5. crear la derivación;
6. generar notificaciones;
7. mantener consistente el estado de la Solicitud.

La misma regla aplica a:

- crear Solicitud con distribución inicial;
- incorporar un área;
- cambiar `PRINCIPAL ↔ ADJUNTA`;
- devolver;
- finalizar período;
- anular Solicitud.

---

# 4. Estados globales recomendados para `Solicitud`

Inicialmente se recomienda mantener pocos estados:

```text
REGISTRADA
EN_GESTION
FINALIZADA
ANULADA
```

## `REGISTRADA`

La Solicitud existe administrativamente, pero todavía puede no haber iniciado su flujo operativo.

Puede ser útil para:

- importación Legacy;
- futuros registros previos a distribución;
- casos donde Solicitud se crea antes de abrir áreas.

## `EN_GESTION`

La Solicitud ya se encuentra en el flujo operativo.

Normalmente existe al menos un período de área abierto.

## `FINALIZADA`

Estado terminal global.

La regla definitiva para llegar aquí se definirá junto con la etapa final de respuesta/pago.

## `ANULADA`

El trámite fue cancelado administrativamente.

---

# 5. Fechas globales de `Solicitud`

```text
fecha_registro
fecha_inicio_gestion
fecha_limite
fecha_cierre
```

## `fecha_registro`

Fecha real en que la Solicitud nació administrativamente.

## `fecha_inicio_gestion`

Fecha real en que entró por primera vez al flujo operativo.

Normalmente se establece cuando se abre el primer período de área y no debe cambiarse por reingresos posteriores.

## `fecha_limite`

Vencimiento global, si existe.

## `fecha_cierre`

Fecha global de finalización o anulación.

No sustituye las fechas de cierre de los períodos de área.

---

# 6. Estado de `SolicitudAsignacionPeriodo`

El período necesita una máquina de estados simple:

```text
ABIERTO
CERRADO
```

La razón de cierre se almacena separadamente en `tipo_cierre`.

---

# 7. Tipo de participación del período

Cada período debe tener exactamente uno de:

```text
PRINCIPAL
ADJUNTA
```

Una misma área no puede ser simultáneamente `PRINCIPAL` y `ADJUNTA` dentro del mismo período.

Una Solicitud sí puede tener varias áreas trabajando en paralelo. En esta versión **no se impone que exista una sola área PRINCIPAL**, porque esa regla todavía depende del negocio.

El tipo de participación debe vivir en:

```text
SolicitudAsignacionPeriodo
```

no en `SolicitudAsignacion`.

Esto permite que una misma área tenga distintos papeles en distintos momentos sin destruir el historial.

---

# 8. Tipos de cierre del período

Se recomienda:

```text
FINALIZADO
DERIVADO
RETIRADO
RECHAZADO
ANULADO
CAMBIO_PARTICIPACION
```

## `FINALIZADO`

El área terminó correctamente esa intervención.

## `DERIVADO`

El área terminó esa intervención porque trasladó el trabajo hacia otra área.

## `RETIRADO`

El área deja de participar sin una derivación directa.

## `RECHAZADO`

El área determina formalmente que no corresponde asumir esa intervención.

## `ANULADO`

El período nunca debió existir o fue creado por un error administrativo.

## `CAMBIO_PARTICIPACION`

El área continúa dentro de la Solicitud, pero cambia su papel:

```text
ADJUNTA → PRINCIPAL
```

o:

```text
PRINCIPAL → ADJUNTA
```

El cambio real de rol se representa cerrando el período anterior y abriendo uno nuevo.

---

# 9. Flujo 1 — Crear Expediente

## Endpoint recomendado

```http
POST /api/expedientes
```

## Objetivo

Registrar el ingreso documental original como una sola operación.

## Entrada conceptual

```text
datos del ciudadano / empresa
datos del documento
asunto
folios
observaciones

archivo principal obligatorio

anexos opcionales
antecedentes opcionales
```

## Tablas creadas

```text
Expediente
ExpedienteArchivo
ExpedienteAntecedente    # cuando corresponda
```

## Archivo principal

El archivo principal debe ser obligatorio.

Se recomienda que `ExpedienteArchivo` distinga:

```text
PRINCIPAL
ANEXO
```

### Invariante recomendada

Un Expediente debe tener:

```text
exactamente 1 archivo PRINCIPAL
0..N archivos ANEXO
```

## No crea todavía

```text
Solicitud
SolicitudAsignacion
SolicitudAsignacionPeriodo
SolicitudDerivacion
```

---

# 10. Flujo 2 — Crear Solicitud con distribución inicial

## Endpoint recomendado

```http
POST /api/solicitudes
```

Este es un endpoint macro.

No debería insertar únicamente la fila `Solicitud`; debe crear la distribución inicial en la misma operación.

## Entrada conceptual

```text
expediente_id
prioridad
fecha_registro
fecha_limite              # opcional
observacion               # opcional

areas:
    - area_id
      tipo_participacion

    - area_id
      tipo_participacion
```

## Validaciones

- El Expediente debe existir.
- El Expediente no debe tener otra Solicitud si la relación es 1:1.
- No debe repetirse la misma área en el payload.
- Cada área debe tener exactamente un tipo de participación.
- El tipo debe ser `PRINCIPAL` o `ADJUNTA`.
- Si la versión actual exige distribución inicial, debe existir al menos un área.
- Las fechas deben ser coherentes.

## Tablas creadas

### Una vez

```text
Solicitud
```

### Por cada área

```text
SolicitudAsignacion
```

### Por cada asignación

```text
SolicitudAsignacionPeriodo
```

con:

```text
numero_ciclo = 1
estado = ABIERTO
tipo_participacion = PRINCIPAL | ADJUNTA
```

### Notificaciones

Por cada área puede crearse:

```text
Notificacion
```

más:

```text
NotificacionUsuario
```

para materializar los usuarios elegibles del área.

### Historial

Se crea:

```text
SolicitudEstadoHistorial
```

## Estado resultante

Si la Solicitud nace ya distribuida:

```text
Solicitud.estado = EN_GESTION
```

`fecha_inicio_gestion` se establece con la fecha real en la que empieza el flujo operativo.

`fecha_registro` puede ser igual o anterior.

---

# 11. La distribución inicial no es una derivación

Aunque en lenguaje administrativo se diga "derivar inicialmente a un área", el modelo no debe crear `SolicitudDerivacion` durante la distribución inicial.

Una derivación necesita:

```text
periodo_origen
        ↓
periodo_destino
```

Durante la creación inicial no existe todavía un período origen.

Por tanto la distribución inicial se representa únicamente mediante:

```text
SolicitudAsignacion
+
SolicitudAsignacionPeriodo
```

---

# 12. Flujo 3 — Consulta de bandeja

Los listados deben simplificarse mediante query params en lugar de multiplicar rutas para cada variante.

## Endpoint recomendado

```http
GET /api/solicitudes
```

## Filtros posibles

```text
?estado=EN_GESTION
?prioridad=CRITICA

?area=<uuid>
?tipo_participacion=PRINCIPAL
?tipo_participacion=ADJUNTA

?usuario=<uuid>
?usuario=me

?periodo_estado=ABIERTO
?sin_operador=true

?creado_por=me

?fecha_desde=
?fecha_hasta=
```

Los conceptos Legacy como:

```text
asignadas
mi-area
adjuntadas
creadas
```

pueden resolverse principalmente mediante filtros.

---

# 13. Endpoint de detalle operativo

## Endpoint

```http
GET /api/solicitudes/{id}
```

El detalle puede devolver, según necesidad:

```text
Solicitud
Expediente resumido
Asignaciones de área
Períodos
Período abierto de cada área
Tipo de participación
Usuarios activos
Derivaciones
Historial global
```

Si el objeto resulta demasiado grande pueden utilizarse:

```text
?include=areas,periodos,usuarios,historial
```

o subrecursos de lectura.

---

# 14. Flujo 4 — Incorporar o reincorporar un área

## Endpoint recomendado

```http
POST /api/solicitudes/{solicitud_id}/incorporar-area
```

## Entrada

```text
area_id
tipo_participacion
motivo                    # opcional/recomendado
```

## Caso A — El área nunca participó

Crea:

```text
SolicitudAsignacion
SolicitudAsignacionPeriodo P1
```

## Caso B — El área participó anteriormente pero está cerrada

Reutiliza:

```text
SolicitudAsignacion
```

y crea:

```text
nuevo SolicitudAsignacionPeriodo
```

con:

```text
numero_ciclo = anterior + 1
```

## Caso C — El área ya tiene período abierto

No se crea otro.

La operación debe indicar que el área ya se encuentra activa.

## También genera

```text
Notificacion
NotificacionUsuario
```

## No crea

```text
SolicitudDerivacion
```

porque no existe necesariamente un origen.

---

# 15. Flujo 5 — Usuario toma un período

## Endpoint recomendado

```http
POST /api/periodos/{periodo_id}/tomar
```

## Objetivo

Registrar que el usuario autenticado empieza a trabajar por el área durante ese período.

## Validaciones

- El período debe estar `ABIERTO`.
- El usuario no debe tener ya una participación abierta en el mismo período.
- La pertenencia real del usuario al área se validará cuando se implemente autorización fina.

## Crea

```text
SolicitudAsignacionUsuario
```

con:

```text
usuario = request.user
fecha_inicio = fecha real
asignado_por = request.user
```

## No cambia

```text
SolicitudAsignacion
```

## No crea

```text
SolicitudDerivacion
```

## Estado derivado

No hace falta guardar un estado `TOMADO`.

Puede calcularse:

```text
Periodo ABIERTO + 0 usuarios activos
= PENDIENTE DE TOMAR

Periodo ABIERTO + >= 1 usuario activo
= EN ATENCION
```

---

# 16. Flujo 6 — Agregar otro usuario

## Endpoint recomendado

```http
POST /api/periodos/{periodo_id}/usuarios
```

## Entrada

```text
usuario_id
rol                     # opcional
```

## Crea

```text
SolicitudAsignacionUsuario
```

Agregar un colaborador no cambia de área, no abre otro período y no genera derivación.

---

# 17. Flujo 7 — Retirar un usuario

## Endpoint recomendado

```http
POST /api/participaciones-usuario/{id}/retirar
```

## Modifica

```text
SolicitudAsignacionUsuario.fecha_fin
SolicitudAsignacionUsuario.retirado_por
SolicitudAsignacionUsuario.motivo_retiro
```

Puede quedar:

```text
Periodo ABIERTO
+
0 usuarios activos
```

Esto es válido y representa trabajo pendiente sin operador actual.

---

# 18. Flujo 8 — Área incorporada por error

Un área incorporada por error no debería borrarse físicamente del historial.

## Endpoint recomendado

```http
POST /api/periodos/{periodo_id}/anular
```

## Uso de `ANULADO`

Se recomienda cuando:

> el período nunca debió existir.

## Uso de `RETIRADO`

Se recomienda cuando:

> la participación sí fue válida, pero posteriormente dejó de ser necesaria.

## Modifica

```text
SolicitudAsignacionPeriodo.estado = CERRADO
SolicitudAsignacionPeriodo.fecha_fin
SolicitudAsignacionPeriodo.tipo_cierre
SolicitudAsignacionPeriodo.finalizado_por
SolicitudAsignacionPeriodo.motivo_cierre
```

La `SolicitudAsignacion` permanece.

Si el área debe volver después, se abre otro período sobre la misma asignación.

---

# 19. Flujo 9 — Reingreso de un área

Un período cerrado nunca se reabre.

Se reutiliza:

```http
POST /api/solicitudes/{solicitud_id}/incorporar-area
```

La operación encuentra la `SolicitudAsignacion` existente y crea un nuevo ciclo.

```text
SolicitudAsignacion Arquitectura
    |
    +-- P1 CERRADO
    +-- P2 CERRADO
    +-- P3 ABIERTO
```

---

# 20. Flujo 10 — Cambio `ADJUNTA ↔ PRINCIPAL`

Un cambio real de participación debe aprovechar el modelo de períodos.

## Endpoint recomendado

```http
POST /api/periodos/{periodo_id}/cambiar-participacion
```

## Entrada

```text
nuevo_tipo_participacion
motivo
```

## Operación

### Cierra el período actual

```text
estado = CERRADO
tipo_cierre = CAMBIO_PARTICIPACION
fecha_fin = fecha real
```

### Abre un nuevo período

Sobre la misma:

```text
SolicitudAsignacion
```

crea:

```text
nuevo numero_ciclo
nuevo tipo_participacion
estado = ABIERTO
fecha_inicio = fecha real
```

## No crea

```text
SolicitudDerivacion
```

porque el área no cambió.

## Corrección de digitación

Si el período acaba de crearse con el tipo incorrecto y todavía no ocurrió actividad real, puede permitirse una corrección directa auditada técnicamente.

Cuando el cambio represente un hecho real del negocio, debe cerrarse y abrirse otro período.

---

# 21. Flujo 11 — Derivar hacia otra área

## Endpoint recomendado

```http
POST /api/periodos/{periodo_origen_id}/derivar
```

## Entrada

```text
area_destino_id
tipo_participacion_destino
motivo
observacion              # opcional
```

## Validaciones

- El período origen debe estar `ABIERTO`.
- El área destino debe existir.
- El destino pertenece a la misma Solicitud.
- No debe derivarse hacia el mismo período.
- Debe comprobarse si el área destino ya tiene un período abierto.

## Paso 1 — Cerrar origen

```text
estado = CERRADO
tipo_cierre = DERIVADO
fecha_fin = fecha real
finalizado_por = request.user
```

## Paso 2 — Obtener asignación destino

Busca:

```text
SolicitudAsignacion(solicitud, area_destino)
```

Si existe:

```text
reutilizar
```

Si no:

```text
crear
```

## Paso 3 — Obtener período destino

### Destino sin período abierto

Crear:

```text
SolicitudAsignacionPeriodo
```

con el siguiente ciclo.

### Destino con período abierto

No crear otro período simultáneo.

La derivación puede apuntar al período abierto existente.

Esto mantiene la regla:

```text
máximo 1 período abierto
por SolicitudAsignacion
```

## Paso 4 — Crear movimiento

```text
SolicitudDerivacion
```

con:

```text
periodo_origen
periodo_destino
tipo = DERIVACION
derivado_por
fecha_derivacion
motivo
```

## Paso 5 — Notificar

```text
Notificacion
NotificacionUsuario
```

## Transacción

Todo debe ocurrir atómicamente.

No puede quedar un origen cerrado si falló la creación/resolución del destino.

---

# 22. Flujo 12 — Devolver

La devolución utiliza la misma infraestructura de movimiento entre períodos.

## Endpoint recomendado

```http
POST /api/periodos/{periodo_id}/devolver
```

La operación realiza:

```text
cerrar origen
+
obtener/reabrir destino
+
crear SolicitudDerivacion tipo DEVOLUCION
+
notificar
```

La derivación anterior nunca se elimina ni se revierte.

---

# 23. Flujo 13 — Finalizar período de un área

## Endpoint recomendado

```http
POST /api/periodos/{periodo_id}/finalizar
```

## Objetivo

Indicar que esa intervención concreta del área terminó correctamente.

## Validaciones

- El período debe estar `ABIERTO`.
- No puede estar previamente cerrado.
- Los requisitos documentales específicos se incorporarán posteriormente.
- La respuesta final del área queda fuera del alcance actual.

## Modifica

```text
SolicitudAsignacionPeriodo.estado = CERRADO
SolicitudAsignacionPeriodo.tipo_cierre = FINALIZADO
SolicitudAsignacionPeriodo.fecha_fin
SolicitudAsignacionPeriodo.finalizado_por
```

## Importante

Esto NO implica automáticamente:

```text
Solicitud.estado = FINALIZADA
```

Solo significa:

> esa intervención de esa área terminó.

El área puede reingresar posteriormente mediante otro período.

---

# 24. Evaluación después de cada cierre

Después de cerrar un período por:

```text
FINALIZADO
DERIVADO
RETIRADO
RECHAZADO
ANULADO
CAMBIO_PARTICIPACION
```

se recomienda ejecutar internamente:

```text
evaluar_estado_operativo_solicitud(solicitud)
```

Este servicio puede calcular:

```text
áreas activas
períodos abiertos
principales abiertos
adjuntas abiertas
áreas finalizadas
áreas derivadas
áreas retiradas
áreas anuladas
```

No necesariamente modifica `Solicitud.estado`.

Su objetivo inicial es devolver una fotografía operativa coherente.

---

# 25. Punto futuro de integración con pago / siguiente etapa

Todavía falta definir exactamente cuándo una Solicitud puede pasar a pago o a la etapa final.

La condición podría depender de:

- que determinadas áreas `PRINCIPAL` hayan finalizado;
- que no existan períodos principales abiertos;
- que una cantidad mínima de áreas haya finalizado;
- especialidades requeridas según el tipo de trámite;
- tratamiento de períodos derivados;
- tratamiento de adjuntas todavía abiertas.

## Recomendación actual

No crear todavía un estado rígido como:

```text
HABILITADA_PAGO
```

hasta conocer la regla real.

Puede exponerse un resumen calculado:

```http
GET /api/solicitudes/{id}/estado-operativo
```

con información como:

```text
periodos_abiertos
principales_abiertos
adjuntas_abiertas
areas_finalizadas
lista_para_siguiente_etapa
```

`lista_para_siguiente_etapa` puede quedar inicialmente como una evaluación provisional del service y evolucionar cuando se defina la regla de pago.

---

# 26. Flujo 14 — Anular Solicitud

## Endpoint recomendado

```http
POST /api/solicitudes/{id}/anular
```

## Solicitud

```text
estado = ANULADA
fecha_cierre = fecha real
```

## Períodos abiertos

Cerrar todos:

```text
estado = CERRADO
tipo_cierre = ANULADO
fecha_fin = fecha real
```

## Participaciones de usuario abiertas

Cerrar también sus participaciones.

## Historial

Crear:

```text
SolicitudEstadoHistorial
```

## No eliminar

La anulación conserva toda la historia previa.

---

# 27. `SolicitudAsignacion` como relación estable

Conceptualmente debe quedar simple:

```text
SolicitudAsignacion
-------------------
solicitud
area
fecha_incorporacion
incorporado_por
observacion
```

Responde únicamente:

> ¿Esta área participa o participó alguna vez en esta Solicitud?

No responde:

- si está activa actualmente;
- si es principal o adjunta actualmente;
- si finalizó;
- qué usuario la está atendiendo.

---

# 28. `SolicitudAsignacionPeriodo` como centro operativo

```text
SolicitudAsignacionPeriodo
--------------------------
asignacion
numero_ciclo

tipo_participacion
    PRINCIPAL
    ADJUNTA

estado
    ABIERTO
    CERRADO

fecha_inicio
fecha_fin

tipo_cierre
    FINALIZADO
    DERIVADO
    RETIRADO
    RECHAZADO
    ANULADO
    CAMBIO_PARTICIPACION

iniciado_por
finalizado_por
motivo_cierre
observacion
```

Esta tabla es la fuente de verdad principal del flujo operativo de las áreas.

---

# 29. Estado operativo derivado del área

No se recomienda agregar otro estado operativo en `SolicitudAsignacion`.

## Activa

```text
existe período ABIERTO
```

## Activa como principal

```text
período ABIERTO
+
tipo_participacion = PRINCIPAL
```

## Activa como adjunta

```text
período ABIERTO
+
tipo_participacion = ADJUNTA
```

## Sin intervención activa

```text
no existe período ABIERTO
```

El último período indica cómo terminó su última participación.

---

# 30. Estado operativo derivado del usuario

## Pendiente de tomar

```text
Periodo ABIERTO
+
0 SolicitudAsignacionUsuario activos
```

## En atención

```text
Periodo ABIERTO
+
>= 1 SolicitudAsignacionUsuario activo
```

No se necesitan estados persistidos adicionales para representar estas dos situaciones.

---

# 31. Notificaciones dentro del flujo

Las notificaciones son consecuencia del flujo, no su fuente de verdad.

## Crear Solicitud / distribución inicial

Genera aviso de nueva asignación al área.

## Incorporar o reincorporar área

Genera nueva notificación al área.

## Derivar

Genera notificación para el destino.

## Devolver

Genera notificación para el destino.

## Lectura

`NotificacionUsuario` registra:

```text
vista_at
abierta_at
descartada_at
```

Abrir una notificación no significa tomar el trabajo.

Tomar el trabajo no significa finalizar el período.

---

# 32. Endpoints macro recomendados

| Método | Endpoint | Operación |
|---|---|---|
| `POST` | `/api/expedientes` | Crear expediente + principal + anexos + antecedentes |
| `GET` | `/api/expedientes` | Listar/filtrar expedientes |
| `GET` | `/api/expedientes/{id}` | Detalle del expediente |
| `POST` | `/api/solicitudes` | Crear Solicitud + distribución inicial |
| `GET` | `/api/solicitudes` | Bandeja con filtros/query params |
| `GET` | `/api/solicitudes/{id}` | Detalle operativo |
| `POST` | `/api/solicitudes/{id}/incorporar-area` | Incorporar o reincorporar área |
| `GET` | `/api/solicitudes/{id}/estado-operativo` | Resumen calculado del flujo |
| `POST` | `/api/periodos/{id}/tomar` | Autoasignarse |
| `POST` | `/api/periodos/{id}/usuarios` | Agregar usuario participante |
| `POST` | `/api/participaciones-usuario/{id}/retirar` | Retirar usuario |
| `POST` | `/api/periodos/{id}/cambiar-participacion` | Cerrar ciclo y abrir otro PRINCIPAL/ADJUNTA |
| `POST` | `/api/periodos/{id}/derivar` | Derivar a otra área |
| `POST` | `/api/periodos/{id}/devolver` | Devolver a otra área/período |
| `POST` | `/api/periodos/{id}/finalizar` | Finalizar intervención |
| `POST` | `/api/periodos/{id}/retirar` | Retirar área del flujo |
| `POST` | `/api/periodos/{id}/anular` | Invalidar un período creado por error |
| `POST` | `/api/solicitudes/{id}/anular` | Anular Solicitud globalmente |
| `GET` | `/api/notificaciones` | Consultar notificaciones |
| `POST` | `/api/notificaciones/{id}/vista` | Registrar vista personal |

---

# 33. Impacto de cada operación en tablas

| Operación | Crea | Modifica |
|---|---|---|
| Crear Expediente | `Expediente`, `ExpedienteArchivo`, `ExpedienteAntecedente` | — |
| Crear Solicitud | `Solicitud`, `SolicitudAsignacion`, `SolicitudAsignacionPeriodo`, `SolicitudEstadoHistorial`, `Notificacion`, `NotificacionUsuario` | — |
| Incorporar área nueva | `SolicitudAsignacion`, `SolicitudAsignacionPeriodo`, `Notificacion`, `NotificacionUsuario` | — |
| Reincorporar área | `SolicitudAsignacionPeriodo`, `Notificacion`, `NotificacionUsuario` | — |
| Tomar período | `SolicitudAsignacionUsuario` | — |
| Agregar usuario | `SolicitudAsignacionUsuario` | — |
| Retirar usuario | — | `SolicitudAsignacionUsuario` |
| Cambiar participación | nuevo `SolicitudAsignacionPeriodo` | período anterior |
| Derivar | asignación destino si falta, período destino si falta, `SolicitudDerivacion`, `Notificacion`, `NotificacionUsuario` | período origen |
| Devolver | período destino si falta, `SolicitudDerivacion`, `Notificacion`, `NotificacionUsuario` | período origen |
| Finalizar período | — | `SolicitudAsignacionPeriodo` |
| Retirar área | — | `SolicitudAsignacionPeriodo` |
| Anular período | — | `SolicitudAsignacionPeriodo` |
| Anular Solicitud | `SolicitudEstadoHistorial` | `Solicitud`, períodos y participaciones abiertas |
| Ver notificación | — | `NotificacionUsuario` |

---

# 34. Operaciones obligatoriamente transaccionales

Como mínimo:

```text
crear_expediente()
crear_solicitud_con_distribucion()
incorporar_area()
cambiar_participacion()
derivar_periodo()
devolver_periodo()
finalizar_periodo()
anular_solicitud()
```

Si falla cualquier paso:

```text
se revierte toda la operación
```

No deben existir estados intermedios parcialmente persistidos.

---

# 35. Concurrencia

## Apertura de períodos

No deben existir dos períodos abiertos para la misma `SolicitudAsignacion`.

## Número de ciclo

No se recomienda generar el siguiente ciclo únicamente con:

```text
COUNT(*) + 1
```

sin protección transaccional.

## Autoasignación

Dos peticiones simultáneas no deben crear dos participaciones abiertas idénticas para el mismo usuario.

## Derivación

Dos usuarios no deben poder cerrar y derivar simultáneamente el mismo período hacia destinos distintos.

El service debe bloquear o revalidar el período dentro de la transacción.

---

# 36. Idempotencia

Los endpoints de acción deben manejar reintentos de forma segura.

Ejemplo:

```http
POST /api/periodos/123/finalizar
```

si el período ya está cerrado, no debe generar un segundo cierre.

Puede responder con un conflicto de negocio o devolver el estado actual según la convención del API.

Esto aplica también a:

- tomar;
- retirar;
- derivar;
- devolver;
- cambiar participación;
- anular.

---

# 37. No eliminar historial operativo

No debería existir borrado funcional para:

```text
SolicitudAsignacion
SolicitudAsignacionPeriodo
SolicitudAsignacionUsuario histórico
SolicitudDerivacion
SolicitudEstadoHistorial
```

Las correcciones se expresan mediante:

```text
cierre
anulación
retiro
nuevo período
nuevo evento
```

Esto protege trazabilidad y métricas.

---

# 38. Flujo global resumido

```text
1. POST /expedientes
        |
        +-- Expediente
        +-- Archivo PRINCIPAL
        +-- Anexos
        +-- Antecedentes
        |
        v

2. POST /solicitudes
        |
        +-- Solicitud
        |
        +-- Área A
        |      +-- SolicitudAsignacion
        |      +-- Periodo P1
        |
        +-- Área B
        |      +-- SolicitudAsignacion
        |      +-- Periodo P1
        |
        +-- Notificaciones
        |
        v

3. OPERACIÓN DE ÁREAS EN PARALELO
        |
        +-- tomar
        +-- agregar usuario
        +-- retirar usuario
        |
        +-- incorporar área
        +-- reingresar área
        |
        +-- cambiar PRINCIPAL / ADJUNTA
        |
        +-- derivar
        +-- devolver
        |
        +-- retirar
        +-- anular
        |
        +-- finalizar período
        |
        v

4. EVALUAR ESTADO OPERATIVO
        |
        +-- períodos abiertos
        +-- principales abiertos
        +-- adjuntas abiertas
        +-- áreas finalizadas
        |
        v

5. PUNTO DE SALIDA
        |
        +-- futura regla de pago
        +-- futura respuesta final
        +-- futuro cierre institucional
```

---

# 39. Ejemplo estructural de cambio de participación

```text
SolicitudAsignacion: Arquitectura

P1
ADJUNTA
ABIERTO

        ↓ cambiar-participacion

P1
ADJUNTA
CERRADO / CAMBIO_PARTICIPACION

P2
PRINCIPAL
ABIERTO
```

No se crea otra `SolicitudAsignacion`.

---

# 40. Ejemplo estructural de error y reincorporación

```text
Arquitectura/P1
PRINCIPAL
ABIERTO

        ↓ error administrativo

Arquitectura/P1
PRINCIPAL
CERRADO / ANULADO

        ↓ posteriormente sí debe participar

Arquitectura/P2
ADJUNTA
ABIERTO
```

---

# 41. Ejemplo estructural de derivación y devolución

```text
Arquitectura/P1
ABIERTO

        ↓ DERIVACION

Arquitectura/P1
CERRADO / DERIVADO

Estructuras/P1
ABIERTO

        ↓ DEVOLUCION

Estructuras/P1
CERRADO / DERIVADO

Arquitectura/P2
ABIERTO
```

Las relaciones institucionales permanecen:

```text
SolicitudAsignacion Arquitectura
SolicitudAsignacion Estructuras
```

---

# 42. Qué no debe hacer el frontend

El frontend no debe conocer la secuencia interna de persistencia.

No debería implementar:

```text
1. cerrar origen
2. crear destino
3. crear derivación
4. crear notificación
```

Debe enviar únicamente la intención:

```text
DERIVAR
```

El backend garantiza consistencia.

---

# 43. Respuesta recomendada de endpoints macro

Después de una operación importante conviene devolver un snapshot suficiente para actualizar la interfaz.

Por ejemplo, `derivar` podría devolver conceptualmente:

```text
solicitud_id
periodo_origen
periodo_destino
derivacion
estado_operativo_actual
```

No es necesario devolver todos los modelos completos.

---

# 44. Capa de servicios recomendada

Los endpoints deberían ser delgados.

Servicios conceptuales:

```text
crear_expediente()
crear_solicitud_con_distribucion()
incorporar_area()
tomar_periodo()
agregar_usuario_periodo()
retirar_usuario_periodo()
cambiar_participacion()
derivar_periodo()
devolver_periodo()
cerrar_periodo()
anular_solicitud()
evaluar_estado_operativo()
```

Flujo recomendado:

```text
Endpoint
   ↓
validación HTTP / schema
   ↓
Service de dominio
   ↓
validaciones de negocio
   ↓
transaction.atomic
   ↓
operaciones en modelos
   ↓
notificaciones / historial
   ↓
resultado coherente
```

---

# 45. Decisiones abiertas para una siguiente etapa

## Respuesta final

Todavía no se define:

- documento consolidado;
- quién lo genera;
- quién lo aprueba;
- firma;
- versionado final.

## Pago

Todavía debe definirse:

- qué áreas deben haber finalizado;
- si cuentan solamente períodos `PRINCIPAL`;
- si hay una cantidad mínima;
- si depende del tipo de trámite;
- cómo afectan derivaciones y devoluciones;
- cómo afectan adjuntas todavía abiertas.

## Cierre global

Todavía debe definirse si es:

- automático;
- manual;
- aprobado por supervisor;
- posterior a pago;
- posterior a respuesta final.

Estas decisiones no deben bloquear la implementación del flujo operativo descrito aquí.

---

# 46. Principios finales

1. `Expediente` representa lo recibido.
2. `Solicitud` representa el trámite global.
3. `SolicitudAsignacion` representa que un área participa o participó.
4. `SolicitudAsignacionPeriodo` representa cada intervención temporal del área.
5. `PRINCIPAL / ADJUNTA` pertenece al período.
6. Un cambio real de participación cierra un período y abre otro.
7. Un período finalizado puede ser seguido por otro período de la misma área.
8. Los usuarios participan dentro de períodos.
9. Cambiar usuarios no equivale a derivar.
10. La distribución inicial no es una derivación.
11. Derivar/devolver son operaciones macro y transaccionales.
12. Los períodos históricos no se reabren.
13. Los errores administrativos se anulan; no se borran del historial.
14. Las notificaciones son consecuencia del flujo, no su fuente de verdad.
15. Los GET consultan y filtran; las acciones de negocio modifican.
16. La etapa final de respuesta/pago se conecta después sin rediseñar el núcleo.

---

# 47. Regla mental para crear nuevos endpoints

Antes de crear una ruta nueva:

```text
¿Es solamente consulta?
    ↓
GET + query params

¿Es una corrección técnica sin significado histórico?
    ↓
PATCH excepcional y auditado

¿Representa un hecho administrativo?
    ↓
endpoint de acción

¿El hecho modifica varias tablas?
    ↓
service transaccional

¿El cambio reemplaza una etapa real del pasado?
    ↓
cerrar registro anterior + crear uno nuevo
```

El API debe hablar el lenguaje del negocio:

```text
crear
incorporar
tomar
retirar
cambiar participación
derivar
devolver
finalizar
anular
```

y no únicamente el lenguaje de las tablas.
