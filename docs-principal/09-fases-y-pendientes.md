# Fases y pendientes

## Fotografía actual

| Capacidad | Estado | Evidencia resumida |
|---|---|---|
| Modelos de expediente/solicitud | Implementado | `backend/modules/tramites/domain/models`. |
| Modelos de asignaciones | Implementado estructural | `backend/modules/asignaciones/domain/models`. |
| Crear expediente con archivos | Implementado | Controller, flujo y core de tramites. |
| Crear solicitud con áreas | Implementado parcial | Siempre `EN_GESTION`; faltan reglas objetivo. |
| Creación completa | Implementado parcial | Atómica en BD; el storage externo requiere compensación. Faltan historiales/destinatarios. |
| Historial global | Implementado inconsistente | Catálogo no coincide con Solicitud; fecha no histórica. |
| Estado/historial del período | Parcial | Tabla/servicio existen; no hay snapshot objetivo integrado. |
| Notificación institucional | Parcial | Se crea por área; no materializa usuarios. |
| Participación de usuarios | Solo modelo | Sin endpoints/servicios. |
| Respuestas | Solo modelo e inconsistente para borradores | Sin endpoints/servicios; `emitido_por` es obligatorio incluso en `BORRADOR`. |
| Listados y detalles backend | Ausente | Solo POST de creación registrados. |
| Frontend Mesa de Partes | Ausente | Sin rutas/features específicas. |
| Tests del historial de período | Parcial/roto | Fixtures usan campos incompatibles con modelos actuales. |

## Contradicciones técnicas a resolver antes de implementar

1. `Solicitud.estado` real no coincide con el catálogo objetivo ni con su historial.
2. `SolicitudEstadoHistorial` usa `fecha auto_now_add` y no tiene `origen`.
3. `SolicitudAsignacionPeriodo.estado` real es `ABIERTO/CERRADO`, mientras el historial usa `PENDIENTE/EN_GESTION/CERRADO`.
4. El historial de período existe, pero los flujos no lo crean ni actualizan un snapshot operativo.
5. `SolicitudAsignacion.tipo_participacion` duplica el tipo del período.
6. `bloquea_cierre` anticipa una regla global todavía no definida.
7. El schema de solicitud exige áreas, aunque el objetivo permite `REGISTRADA` sin distribución.
8. Los flujos crean `Notificacion` sin `NotificacionUsuario` y sin enlazar el período creado.
9. Los presenters de creación no incluyen asignaciones reales pese a que el schema declara la lista.
10. No existen constraints para archivo principal único, período abierto único ni participante abierto único.
11. Existen derivación/devolución en modelo/constants, pero están descartadas como flujo objetivo normal.
12. `SolicitudAsignacionRespuesta.emitido_por` es obligatorio para `BORRADOR`, por lo que el modelo no separa creador del borrador y emisor formal.

## Fase 1: alinear el núcleo persistente

Objetivo: hacer que las tablas representen las decisiones confirmadas antes de sumar endpoints.

- Alinear estados globales y su historial.
- Definir `SolicitudAsignacionPeriodo.estado` como estado institucional autoritativo.
- Integrar historial inicial y transiciones.
- Resolver duplicidad de tipo en asignación estable.
- Diferir o retirar semántica de `bloquea_cierre` sin perder datos existentes si los hubiera.
- Agregar constraints de unicidad y checks.
- Corregir migraciones nuevas sin editar migraciones ya aplicadas/compartidas.
- Reparar fixtures y pruebas conforme al contrato V2.

## Fase 2: completar creación

- Permitir solicitud `REGISTRADA` sin áreas.
- Establecer `fecha_inicio_gestion` en primera distribución.
- Crear períodos `PENDIENTE` e historial inicial.
- Materializar `NotificacionUsuario` desde afiliaciones vigentes.
- Enlazar notificación con período.
- Validar exactamente un archivo principal.
- Incorporar antecedentes en el flujo si el payload los admite.
- Proteger numeración e idempotencia.

## Fase 3: consultas y detalle

- Listados paginados de expedientes, solicitudes y notificaciones.
- Detalle documental de expediente.
- Detalle integral de solicitud.
- Filtros por estado global, área, tipo, estado de período, participante, respuesta y fechas.
- Selectors optimizados con `select_related`, `prefetch_related` y agregados.

## Fase 4: operación de áreas

- Incorporar/reincorporar área.
- Iniciar gestión explícitamente.
- Tomar y agregar participantes.
- Retirar participantes.
- Finalizar período.
- Cerrar por asignación errónea e incorporar área correcta.
- Cambiar participación cerrando/abriendo ciclos.

No implementar devolución o transferencia como atajo.

## Fase 5: respuestas y notificaciones

- Como recomendación funcional todavía no implementada, agregar `creado_por` para el borrador y permitir `emitido_por = NULL` hasta `EMITIDA`; como alternativa mínima, hacer nullable el emisor durante `BORRADOR`.
- Crear borrador, emitir, anular y rectificar respuestas.
- Tratar `RECTIFICADA` como terminal y crear la corrección en una fila/version nueva.
- Mantener emisión separada de finalización.
- Endpoints explícitos de vista, apertura y descarte.
- Bandeja institucional individualizada.
- Métricas básicas derivadas de hechos.

## Fase 6: frontend

- Formulario de creación completa.
- Bandeja y detalle de solicitudes.
- Bandeja de notificaciones.
- Listado y detalle de expedientes.
- Acciones contextuales según estado de negocio, sin motor de roles todavía.
- Actualización de snapshots e invalidación de queries después de acciones macro.

## Futuro importante, no bloqueante

| Tema | Qué falta definir |
|---|---|
| Cierre global | Condiciones, actor, automatismo y relación con respuestas/pago. |
| Comentarios/chat | Alcance global o por área/período, menciones, adjuntos y notificaciones. |
| Permisos | Acciones por perfil, área, cargo y delegación. |
| Respuesta final consolidada | Documento, aprobación, firma y versionado. |
| Pago/siguiente etapa | Condiciones de habilitación. |
| Analítica | SLA, tiempo laboral, percentiles, backlog y calidad. |
| Alertas | Solicitudes registradas sin distribución, vencimientos y antigüedad. |

## Decisiones ya cerradas

- `Expediente 1:1 Solicitud`.
- Varias áreas principales y adjuntas en paralelo.
- Asignación estable y ciclos por período.
- Períodos históricos no se reabren.
- Estado institucional explícito e independiente.
- Varios usuarios activos, sin mínimo ni responsable único.
- Responder y finalizar son acciones independientes.
- No existe devolución/transferencia normal.
- Error de asignación se conserva con `ASIGNACION_ERRONEA`.
- Cambio de participación abre un nuevo ciclo.
- Notificación al área; interacción y toma separadas.
- Incorporación registra actor, fecha y motivo sin `periodo_origen`.
- Roles/permisos no se diseñan en esta fase.

## Criterio de cierre de esta documentación

La especificación queda validada cuando los responsables funcionales confirman:

- entidades y autoridad de datos;
- transiciones institucionales;
- efectos por operación;
- independencia de dimensiones;
- experiencia de bandejas/detalles;
- pendientes deliberados.

Después de esa validación, otros subagentes pueden convertir cada fase en especificaciones técnicas y tareas de implementación sin reconstruir el flujo desde documentos históricos.

Volver al [mapa principal](README.md).
