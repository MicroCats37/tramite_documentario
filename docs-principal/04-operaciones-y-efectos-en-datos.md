# Operaciones y efectos en datos

## Cómo leer este catálogo

Cada operación expresa una intención de negocio. Todas las rutas backend se documentan completas bajo el prefijo real `/api`; `{id}` representa siempre un UUID. Sus schemas técnicos deben componerse con bloques general, específico e identidad según `contract/SCHEMA_DRY_INTENTION.md`, y todo schema HTTP debe heredar `BaseSchema`.

## Matriz resumida

| Operación | Inserta | Actualiza |
|---|---|---|
| Crear expediente | Expediente, archivos, antecedentes opcionales | Nada |
| Crear solicitud registrada | Solicitud, historial global | Nada |
| Crear solicitud distribuida | Solicitud, historial global, asignaciones, períodos, historiales, notificaciones y destinatarios | Nada |
| Creación completa | Expediente, archivos, solicitud, historiales, asignaciones, períodos, notificaciones y destinatarios | Nada |
| Distribuir/incorporar área | Asignación si falta, período, historial, notificación y destinatarios | Solicitud si era `REGISTRADA` |
| Iniciar gestión del período | Historial de período | Estado del período |
| Tomar/agregar usuario | Participación de usuario | Nada |
| Retirar usuario | Nada | Participación de usuario |
| Registrar/emitir respuesta | Respuesta o nueva versión | Respuesta al emitir/anular/rectificar |
| Finalizar período | Historial de período | Período y participaciones abiertas según política de cierre |
| Corregir asignación errónea | Historial de cierre + estructura del área correcta | Período incorrecto |
| Cambiar participación | Nuevo período, historial inicial y notificación | Período anterior + historial de cierre |
| Ver/abrir/descartar notificación | Nada | NotificacionUsuario |

## 1. Crear expediente

**Intención:** registrar lo recibido sin abrir necesariamente una solicitud.

**Ruta actual:** `POST /api/expedientes/crear`.

**Precondiciones:** usuario autenticado; datos de persona coherentes; asunto presente; exactamente un archivo principal en el objetivo; antecedentes existentes y distintos del expediente nuevo.

**Tablas leídas:** `Expediente` para numeración anual; `Usuario`; antecedentes si se envían.

**Inserts:** una fila `Expediente`; una fila `ExpedienteArchivo` principal; cero o más anexos; cero o más `ExpedienteAntecedente`.

**Updates:** ninguno.

**Historial:** `django-simple-history` registra creación técnica; no existe transición funcional.

**Notificaciones:** ninguna.

**Estado resultante:** expediente sin solicitud.

**Errores e idempotencia:** archivo principal faltante/múltiple, antecedente inexistente o duplicado, datos de persona inválidos. Un rollback de base de datos no elimina archivos externos ya escritos, por lo que aplica la estrategia temporal o compensatoria descrita en la operación 3. Un reintento sin clave idempotente puede duplicar expediente; la numeración anual debe serializarse o protegerse con constraint y reintento.

**Actual:** no crea antecedentes y no exige exactamente un principal; genera `MAX(numero)+1` sin bloqueo.

## 2. Crear solicitud sobre expediente

**Intención:** abrir el caso global para un expediente existente.

**Ruta actual:** `POST /api/solicitudes/crear`.

**Precondiciones comunes:** expediente existente; sin solicitud previa por relación 1:1; fechas coherentes.

### 2A. Crear sin áreas

**Tablas leídas:** `Expediente` y `Solicitud` para validar existencia y cardinalidad.

**Inserts:** `Solicitud` creada directamente en `REGISTRADA`; `SolicitudEstadoHistorial` inicial `null -> REGISTRADA`.

**Updates:** ninguno. `fecha_inicio_gestion` permanece `NULL`.

**Historial:** una fila global inicial con actor, fecha, motivo y origen de registro.

**Notificaciones:** ninguna, porque todavía no existe un área destinataria.

**Estado resultante:** `REGISTRADA`, sin asignaciones ni períodos.

### 2B. Crear con una o más áreas

**Precondiciones adicionales:** áreas existentes, activas y sin duplicados; un tipo de participación por cada área.

**Tablas leídas:** `Expediente`, `Solicitud`, `Area` y `AsignacionUsuario` para materializar destinatarios.

**Inserts:** `Solicitud` creada directamente en `EN_GESTION`, con `fecha_inicio_gestion` establecida desde el inicio; historial global `null -> EN_GESTION`; por cada área una `SolicitudAsignacion`, un período ciclo 1 `PENDIENTE`, su historial inicial, una `Notificacion` y las filas `NotificacionUsuario` correspondientes.

**Updates:** ninguno. No existe una transición intermedia `REGISTRADA -> EN_GESTION` en esta variante.

**Historial:** una fila global inicial `null -> EN_GESTION` y una fila inicial `null -> PENDIENTE` por período.

**Notificaciones:** una notificación institucional por área y sus destinatarios individualizados.

**Estado resultante:** solicitud `EN_GESTION`, `fecha_inicio_gestion` establecida y períodos `PENDIENTE`.

**Errores e idempotencia:** expediente inexistente, conflicto 1:1, área inexistente/inactiva, área repetida. Reintentar sobre el mismo expediente debe devolver conflicto y nunca crear una segunda solicitud.

**Actual:** exige mínimo una área, crea siempre `EN_GESTION`, no fija `fecha_inicio_gestion`, no crea historial de período ni `NotificacionUsuario`.

## 3. Creación completa

**Intención:** crear expediente, solicitud y distribución inicial como una unidad.

**Ruta actual:** `POST /api/solicitudes/crear-completo`.

**Precondiciones:** combinación de crear expediente y solicitud; al menos una área en esta fase prioritaria; áreas únicas.

**Tablas leídas:** numeración de `Expediente`, `Area`, `AsignacionUsuario`, antecedentes opcionales.

**Inserts:** expediente; archivos; antecedentes opcionales; solicitud `EN_GESTION`; historial global; por área asignación, período `PENDIENTE`, historial inicial, notificación y destinatarios.

**Updates:** ninguno.

**Historial:** creación global y por período dentro de la misma transacción.

**Notificaciones:** una institucional por área; una fila individual por usuario elegible al momento del evento.

**Estado resultante:** solicitud `EN_GESTION`, `fecha_inicio_gestion` establecida, períodos en `PENDIENTE`.

**Atomicidad de base de datos y archivos:** `transaction.atomic()` revierte filas y relaciones de la base de datos, pero no elimina archivos que el storage externo ya haya escrito. El flujo debe cargar primero a una ubicación temporal y promover los archivos después del commit, o registrar los objetos creados y ejecutar limpieza compensatoria cuando la transacción falle. No debe afirmarse que el rollback de Django revierte por sí mismo el almacenamiento externo.

**Errores e idempotencia:** cualquier error revierte las escrituras de base de datos de la operación; la estrategia temporal o compensatoria debe evitar archivos huérfanos. Además, se necesita idempotencia HTTP para no duplicar el expediente después de un timeout.

**Actual:** la transacción compuesta existe; faltan antecedentes, fecha de inicio global, historial de período y destinatarios.

## 4. Distribuir por primera vez o incorporar área

**Intención:** abrir participación institucional sin cerrar ninguna otra área.

**Ruta objetivo:** `POST /api/solicitudes/{id}/areas`.

**Entrada conceptual:** `area_id`, `tipo_participacion`, `motivo`, `fecha_incorporacion` opcional para Legacy.

**Precondiciones:** solicitud no terminal; área existente; tipo `PRINCIPAL` o `ADJUNTA`; el área no tiene período abierto.

**Tablas leídas:** `Solicitud`, `Area`, `SolicitudAsignacion`, último período, `AsignacionUsuario`.

**Inserts área nueva:** asignación estable; período ciclo 1 `PENDIENTE`; historial inicial; notificación; destinatarios.

**Inserts reingreso:** nuevo período con `numero_ciclo = último + 1`; historial inicial; notificación; destinatarios. Reutiliza la asignación.

**Updates:** si es la primera distribución, `Solicitud.REGISTRADA -> EN_GESTION` y `fecha_inicio_gestion`; crear historial global. No actualiza otras áreas.

**Historial:** actor, fecha, motivo y origen de creación. No guardar `periodo_origen`.

**Notificaciones:** evento de nueva incorporación/reincorporación al área.

**Estado resultante:** área con período `PENDIENTE`; solicitud `EN_GESTION`.

**Errores e idempotencia:** conflicto si ya está activa; bloqueo de asignación para calcular ciclo; payload repetido no crea otro período.

## 5. Iniciar gestión institucional

**Intención:** declarar que el área comenzó formalmente a gestionar el período.

**Ruta objetivo:** `POST /api/periodos/{id}/iniciar-gestion`.

**Precondiciones:** período en `PENDIENTE`, no cerrado.

**Tablas leídas:** período y último historial.

**Inserts:** historial `PENDIENTE -> EN_GESTION` con actor, fecha, motivo y origen explícito.

**Updates:** `SolicitudAsignacionPeriodo.estado = EN_GESTION`.

**Notificaciones:** ninguna obligatoria.

**Estado resultante:** período `EN_GESTION`, con cero o más participantes y respuestas independientes.

**Errores e idempotencia:** si ya está `EN_GESTION`, el reintento no crea historial duplicado; si está `CERRADO`, conflicto.

**Recomendación:** no usar `AUTOASIGNACION` como origen obligatorio; tomar y empezar gestión son hechos independientes.

## 6. Tomar período

**Intención:** registrar que el usuario autenticado participa en nombre del área.

**Ruta objetivo:** `POST /api/periodos/{id}/tomar`.

**Precondiciones:** período no cerrado; no existe participación abierta del mismo usuario en ese período. La futura autorización validará afiliación.

**Tablas leídas:** período, usuario, participación abierta existente.

**Inserts:** `SolicitudAsignacionUsuario` con `usuario`, `fecha_inicio`, `asignado_por = usuario`.

**Updates:** ninguno en período, solicitud o notificación.

**Historial:** no cambia el historial institucional del período.

**Notificaciones:** ninguna obligatoria.

**Estado resultante:** un participante activo adicional; el período conserva su estado explícito.

**Errores e idempotencia:** duplicado abierto produce conflicto o devuelve la participación existente; constraint condicional recomendado.

## 7. Agregar participante

**Intención:** incorporar otro usuario al mismo período.

**Ruta objetivo:** `POST /api/periodos/{id}/usuarios`.

**Precondiciones:** período no cerrado; usuario existente; sin participación abierta duplicada.

**Tablas leídas:** período, usuario, participaciones.

**Inserts:** `SolicitudAsignacionUsuario`; `rol` opcional y descriptivo.

**Updates, historial y notificaciones:** ninguno obligatorio.

**Estado resultante:** varios usuarios pueden quedar activos; no existe responsable único.

**Errores e idempotencia:** misma protección que tomar.

## 8. Retirar participante

**Intención:** terminar la participación individual sin terminar el área.

**Ruta objetivo:** `POST /api/participaciones-usuario/{id}/retirar`.

**Precondiciones:** participación abierta.

**Tablas leídas:** participación y período para validar que no haya sido alterada concurrentemente.

**Inserts:** ninguno.

**Updates:** `fecha_fin`, `retirado_por`, `motivo_retiro`.

**Historial y notificaciones:** no cambia el estado institucional; notificación no obligatoria.

**Estado resultante:** el período puede quedar con cero usuarios activos y continuar `PENDIENTE` o `EN_GESTION`.

**Errores e idempotencia:** retirar dos veces no duplica efectos; retorna conflicto o estado vigente.

## 9. Crear borrador y emitir respuesta

**Intención:** producir el resultado formal del área sin cerrar automáticamente su período.

**Rutas objetivo:** `POST /api/periodos/{id}/respuestas` y `POST /api/respuestas/{id}/emitir`.

**Precondiciones:** período existente y no inválido; al crear borrador, actor creador conocido; al emitir, contenido o archivo según regla del tipo y emisor existente.

**Tablas leídas:** período, respuestas/versiones previas y usuario actor; al emitir, usuario emisor.

**Inserts objetivo:** nueva `SolicitudAsignacionRespuesta` en `BORRADOR`, conservando al creador y sin emisor formal; una rectificación crea otra fila con su propia versión y no reactiva la fila rectificada.

**Updates al emitir:** `estado = EMITIDA`, `fecha_emision`, `emitido_por`; no actualizar período ni solicitud.

**Historial:** la respuesta conserva versiones/estados; no crea transición de período.

**Notificaciones:** opcionalmente un evento institucional de respuesta cuando exista consumidor definido.

**Estado resultante:** borrador sin emisor o respuesta emitida, mientras el período conserva su estado previo.

**Errores e idempotencia:** emitir una ya emitida no cambia `fecha_emision`; versionado concurrente requiere bloqueo/unicidad `(periodo, version)` recomendada.

**Brecha actual:** el modelo exige `emitido_por` incluso para `BORRADOR`, de modo que este flujo objetivo no está soportado todavía. No existen endpoints ni servicios de respuesta.

**Recomendación funcional, no implementada:** agregar `creado_por` para el autor del borrador y hacer `emitido_por` nullable hasta `EMITIDA`; como alternativa mínima, hacer nullable `emitido_por` durante `BORRADOR`.

## 10. Finalizar período

**Intención:** concluir esa intervención concreta del área.

**Ruta objetivo:** `POST /api/periodos/{id}/finalizar`.

**Precondiciones:** período `PENDIENTE` o `EN_GESTION`; no cerrado. La respuesta solo se exige si una regla específica posterior lo establece.

**Tablas leídas:** período, último historial, participantes y respuestas para devolver snapshot, no para inferir permiso universal.

**Inserts:** historial `estado_actual -> CERRADO` con origen `CIERRE`.

**Updates:** período: `estado=CERRADO`, `fecha_fin`, `tipo_cierre=FINALIZADO`, `finalizado_por`, `motivo_cierre`; cerrar participaciones aún abiertas es una recomendación de consistencia a validar al implementar.

**Notificaciones:** no obligatoria; puede informar a observadores futuros.

**Estado resultante:** área sin período activo. Solicitud permanece `EN_GESTION` hasta una regla global explícita.

**Errores e idempotencia:** un segundo cierre no crea otra transición ni cambia fecha/actor originales.

## 11. Cerrar por asignación errónea e incorporar área correcta

**Intención:** corregir el direccionamiento sin borrar evidencia.

**Ruta objetivo:** `POST /api/periodos/{id}/marcar-asignacion-erronea` y luego la operación de incorporar área; puede exponerse como una macro única si el producto necesita atomicidad conjunta.

**Precondiciones:** período no cerrado; motivo obligatorio; área correcta distinta y no activa si se ejecuta como macro.

**Tablas leídas:** período incorrecto, solicitud, área correcta, asignación/períodos destino.

**Inserts:** historial de cierre; para el área correcta, asignación si falta, nuevo período, historial inicial, notificación y destinatarios.

**Updates:** período incorrecto a `CERRADO`, `tipo_cierre=ASIGNACION_ERRONEA`, fechas y actor.

**Historial:** registrar `estado_actual -> CERRADO` para el período incorrecto, con actor, fecha, motivo y origen `ASIGNACION_ERRONEA`; si se incorpora el área correcta, registrar también `null -> PENDIENTE` para su nuevo período.

**Notificaciones:** no se exige una notificación adicional de cierre al área incorrecta. La incorporación del área correcta genera su notificación institucional y materializa destinatarios.

**Estado resultante:** error preservado y área correcta en `PENDIENTE`.

**Errores e idempotencia:** bloquear período incorrecto y asignación correcta; la macro debe revertir completa si falla el destino.

## 12. Cambiar PRINCIPAL/ADJUNTA

**Intención:** cambiar el papel real del área conservando el papel histórico anterior.

**Ruta objetivo:** `POST /api/periodos/{id}/cambiar-participacion`.

**Precondiciones:** período no cerrado; tipo nuevo diferente; motivo obligatorio.

**Tablas leídas:** período y asignación bloqueados; último ciclo.

**Inserts:** historial de cierre del período anterior; nuevo período en `PENDIENTE`; historial inicial; notificación y destinatarios del nuevo ciclo.

**Updates:** período anterior a `CERRADO`, `tipo_cierre=CAMBIO_PARTICIPACION`, fechas, actor y motivo.

**Historial:** registrar `estado_actual -> CERRADO` en el ciclo anterior y `null -> PENDIENTE` en el nuevo ciclo, ambos con el mismo hecho administrativo como contexto.

**Notificaciones:** generar una notificación institucional asociada al nuevo período y materializar sus destinatarios; no se genera un segundo aviso separado únicamente por cerrar el ciclo anterior.

**Estado resultante:** misma asignación estable, nuevo ciclo con el nuevo tipo.

**Errores e idempotencia:** no aceptar el mismo tipo; no crear dos ciclos ante reintento.

## 13. Interactuar con notificación

**Intención:** auditar comunicación individual sin modificar trabajo institucional.

**Rutas objetivo:** `POST /api/notificaciones/{id}/vista`, `POST /api/notificaciones/{id}/abrir` y `POST /api/notificaciones/{id}/descartar`.

**Precondiciones:** fila `NotificacionUsuario` del actor.

**Tablas leídas:** notificación y relación individual.

**Inserts:** ninguno.

**Updates:** timestamp correspondiente solo si está vacío; conservar primera ocurrencia para métricas.

**Historial:** el timestamp es el hecho auditable.

**Notificaciones:** no genera otra notificación.

**Estado resultante:** cambia únicamente la interacción individual.

**Errores e idempotencia:** reintentos no mueven el timestamp original; un GET nunca marca vista.

## 14. Consultas

**Intención:** leer sin efectos laterales.

**Rutas objetivo:** listados paginados y detalles descritos en [07. Páginas, bandejas y endpoints](07-paginas-bandejas-y-endpoints.md).

**Tablas leídas:** según recurso y filtros.

**Inserts/updates/historial/notificaciones:** ninguno.

**Errores e idempotencia:** filtros inválidos producen error de validación; páginas fuera de rango siguen una convención uniforme. Todos los GET son seguros y repetibles.

## Operaciones globales diferidas

Anular o finalizar globalmente una solicitud, archivar, generar respuesta consolidada y avanzar a pago requieren reglas que aún no están confirmadas. No deben implementarse infiriendo que «todos los períodos están cerrados» basta.

Siguiente lectura: [05. Estados y transiciones](05-estados-y-transiciones.md).
