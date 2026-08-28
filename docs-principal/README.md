# Mesa de Partes: documentación funcional principal

Esta documentación define el flujo funcional que debe validarse antes de continuar la implementación. Contrasta las decisiones vigentes con el backend y el frontend existentes, y separa expresamente lo implementado de lo confirmado, recomendado y futuro.

## Lectura rápida

1. Lea [Visión y alcance](01-vision-y-alcance.md) para entender el vocabulario y los límites.
2. Valide el recorrido en [Flujo end-to-end](02-flujo-end-to-end.md).
3. Valide entidades y campos en [Modelo de datos y tablas](03-modelo-datos-y-tablas.md).
4. Revise los efectos exactos de cada acción en [Operaciones y efectos en datos](04-operaciones-y-efectos-en-datos.md).
5. Confirme las máquinas de estado en [Estados y transiciones](05-estados-y-transiciones.md).
6. Revise la experiencia objetivo en [Páginas, bandejas y endpoints](07-paginas-bandejas-y-endpoints.md).
7. Use la [Guía operativa frontend](10-guia-operativa-frontend.md) para construir rutas, pantallas, contratos y estados UI sin simular capacidades ausentes.

## Mapa documental

| Documento | Pregunta que responde |
|---|---|
| [01. Visión y alcance](01-vision-y-alcance.md) | ¿Qué problema resuelve y qué queda fuera? |
| [02. Flujo end-to-end](02-flujo-end-to-end.md) | ¿Cómo avanza un expediente desde el registro hasta el cierre de intervenciones? |
| [03. Modelo de datos y tablas](03-modelo-datos-y-tablas.md) | ¿Qué representa cada tabla y qué campos son autoridad? |
| [04. Operaciones y efectos](04-operaciones-y-efectos-en-datos.md) | ¿Qué lee, inserta y actualiza cada operación? |
| [05. Estados y transiciones](05-estados-y-transiciones.md) | ¿Qué estados existen y cuáles son independientes? |
| [06. Notificaciones y auditoría](06-notificaciones-y-auditoria.md) | ¿Cómo se separan comunicación, vista y toma? |
| [07. Páginas, bandejas y endpoints](07-paginas-bandejas-y-endpoints.md) | ¿Qué UI y API existen y cuáles deben construirse? |
| [08. Invariantes y concurrencia](08-reglas-invariantes-y-concurrencia.md) | ¿Qué debe proteger la base y qué debe ser atómico? |
| [09. Fases y pendientes](09-fases-y-pendientes.md) | ¿Qué está implementado, parcial, ausente o diferido? |
| [10. Guía operativa frontend](10-guia-operativa-frontend.md) | ¿En qué orden y con qué contratos se construye el frontend de Mesa de Partes? |

## Resumen ejecutivo

- Un `Expediente` representa lo recibido y tiene exactamente una `Solicitud`.
- Una `Solicitud` representa el trámite global. El paralelismo nace de varias áreas en la misma solicitud.
- `SolicitudAsignacion` es la relación estable y única entre solicitud y área.
- `SolicitudAsignacionPeriodo` representa cada ingreso o reingreso del área. Un período cerrado nunca se reabre.
- Cada período tiene un único tipo `PRINCIPAL` o `ADJUNTA`; pueden coexistir varias áreas de ambos tipos.
- El estado institucional del período es explícito: `PENDIENTE`, `EN_GESTION` o `CERRADO`. No se infiere de usuarios ni de respuestas.
- Varios usuarios pueden participar simultáneamente; también es válido que un período abierto no tenga usuarios.
- Una respuesta formal pertenece al período/área. Emitirla no cierra el período.
- Finalizar un período no finaliza la solicitud. Las reglas de cierre global están diferidas.
- Incorporar otra área no cierra el área origen. No existe devolución ni transferencia como flujo normal.
- Las notificaciones se dirigen al área; `NotificacionUsuario` registra interacción individual y `SolicitudAsignacionUsuario` registra la toma real.

## Estado de esta documentación

| Etiqueta | Significado |
|---|---|
| **Actual** | Comportamiento comprobado en modelos, migraciones, servicios, controllers, schemas o frontend. |
| **Objetivo confirmado** | Decisión funcional vigente que debe orientar la implementación. |
| **Recomendación** | Decisión técnica propuesta para hacer consistente el objetivo; requiere aceptación al implementar. |
| **Futuro** | Funcionalidad importante pero deliberadamente fuera de esta fase. |

**Actual:** el backend implementa creación de expediente, creación de solicitud sobre expediente y creación completa. No existen controllers operativos de asignaciones, consultas de bandeja/detalle ni páginas frontend de Mesa de Partes.

**Objetivo confirmado:** esta documentación es la fuente funcional de validación. Los contratos bajo `contract/` siguen siendo normativos para arquitectura, schemas y pruebas.

## Fuentes y precedencia

1. Reglas confirmadas por el usuario y decisiones Engram más recientes.
2. Contratos normativos de `contract/`.
3. Esta documentación principal, una vez validada.
4. Intención de `docs-dev/intencion/`.
5. Implementación actual, usada como evidencia del estado presente y no como definición automática del objetivo.

Cuando una fuente antigua describe devolución, transferencia o estado derivado desde participantes, esa propuesta queda superada por las decisiones confirmadas aquí.

## Checklist de validación funcional

- [ ] La cardinalidad `Expediente 1:1 Solicitud` representa el negocio.
- [ ] La primera distribución, no la toma individual, inicia `EN_GESTION` global.
- [ ] El estado institucional del período puede cambiar sin depender de usuarios o respuestas.
- [ ] Incorporar un área nunca implica cerrar automáticamente otra.
- [ ] El cierre por `ASIGNACION_ERRONEA` y el cambio de participación conservan historial.
- [ ] Las operaciones de respuesta y finalización permanecen independientes.
- [ ] El detalle de solicitud reúne toda la trazabilidad requerida.

Siguiente lectura: [01. Visión y alcance](01-vision-y-alcance.md).
