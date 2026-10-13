# Solicitud: detalle operativo y trazabilidad temporal
## Propósito
Este documento define la experiencia objetivo de la página de detalle de una Solicitud para que funcione como un espacio operativo único: primero explica qué ocurre, luego muestra cómo evolucionó en el tiempo y, finalmente, permite actuar o conversar sin perder el contexto.

Las capturas evidencian tres problemas: la trazabilidad actual se percibe como tarjetas seguidas por una lista cronológica larga; la jerarquía entre estado global, áreas, ciclos, participantes y eventos es débil; y la conversación consume permanentemente cerca de la mitad de la pantalla o aparece como una capa modal no solicitada. El resultado obliga a reconstruir mentalmente el proceso y reduce el espacio útil del contenido principal.

## Decisión de diseño
La página combinará **resumen ejecutivo + flujo operativo temporal** en una sola lectura vertical. No se usarán pestañas `Resumen` / `Trazabilidad` como arquitectura principal. La conversación será un panel lateral integrado, colapsable y no modal que redistribuye el ancho del contenido.

### Principios
- Priorizar el estado actual y la próxima decisión antes que el historial exhaustivo.
- Representar el tiempo espacialmente: izquierda significa antes y derecha significa después.
- Mantener visibles la Solicitud, sus áreas y su estado mientras se consulta la conversación.
- Revelar detalle bajo demanda, sin duplicar el grafo mediante otra lista dominante.
- Mostrar identidad con nombre y contexto de área/rol; nunca usar iniciales como información principal.
- Reutilizar lenguaje, tokens y componentes CIP existentes con borgoña/rojo y neutros sobrios.
- Hacer que la ausencia de acciones sea silenciosa y comprensible, no una colección de controles deshabilitados.

### No objetivos
- No cambiar endpoints, esquemas, reglas, Guardian, permisos ni autorización backend.
- No convertir el chat en `Sheet`, diálogo, modal, overlay, backdrop o elemento flotante.
- No diseñar un dashboard genérico, usar gradientes ni introducir una nueva identidad visual.
- No duplicar la trazabilidad con una segunda lista cronológica larga debajo del grafo.
- No rediseñar los formularios de las operaciones existentes ni alterar su lógica de negocio.
- No exponer `Período` como concepto principal para el usuario; usar `Ciclo` o `Etapa de atención`.

## Arquitectura de información
Orden exacto de arriba hacia abajo:

1. **Encabezado de página:** breadcrumb, `Solicitud {id público}`, descripción breve, estado, prioridad, acción global aplicable y toggle persistente `Conversación`.
2. **Resumen ejecutivo:** identificación del expediente y asunto, estado operativo, fechas clave, alcance activo, áreas responsables y último movimiento.
3. **Flujo operativo:** título, leyenda mínima, controles de escala si son necesarios y grafo temporal horizontal con rail global y carriles por área.
4. **Detalle contextual:** panel en página asociado al ciclo, participante, respuesta o evento seleccionado; cerrado inicialmente.
5. **Información complementaria:** observación general y enlace `Ver expediente` cuando aporten contexto no repetido.
6. **Panel de conversación:** hermano del contenido principal dentro del layout; solo ocupa espacio cuando está abierto.

No crear pestañas primarias entre los puntos 2 y 3. La lectura por defecto debe explicar simultáneamente el estado ejecutivo y el recorrido operativo.

## Wireframes
### Desktop, conversación oculta
```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Solicitudes / Solicitud EXP-2026-0142                                       │
│ Solicitud EXP-2026-0142     [EN GESTIÓN] [Alta] [Finalizar] [Conversación] │
├──────────────────────────────────────────────────────────────────────────────┤
│ RESUMEN EJECUTIVO                                                           │
│ Asunto completo                         Estado: EN GESTIÓN                   │
│ Registro 12 sep │ Inicio 13 sep │ Límite 20 sep │ 2 áreas │ 4 participantes│
│ Responsable: Asesoría Legal (Principal) │ Último movimiento: ...            │
├──────────────────────────────────────────────────────────────────────────────┤
│ FLUJO OPERATIVO                                       [Leyenda] [Escala]     │
│ Estado Solicitud  ● REGISTRADA ───── ● EN_EN_GESTION ──────── FINALIZADA   │
│                  12 sep              13 sep                      pendiente   │
│ ──────────────────────────────────────────────────────────────────────────── │
│ Asesoría Legal   │ [Ciclo 1 PRINCIPAL ═══════════════▶ en curso]    ● evento│
│ Centro Médico    │        [Ciclo 1 ADJUNTA ═══════■]  ● conformidad         │
│                  └────────────────────────────────────────────── tiempo →    │
├──────────────────────────────────────────────────────────────────────────────┤
│ DETALLE CONTEXTUAL DEL ELEMENTO SELECCIONADO                                │
└──────────────────────────────────────────────────────────────────────────────┘
```

El contenido usa todo el ancho disponible. El botón `Conversación` permanece en el encabezado y conserva su posición entre aperturas.

### Desktop, conversación abierta
```text
┌───────────────────────────────────────┬──────────────────────────────────────┐
│ CONTENIDO PRINCIPAL, 50-55%          │ CONVERSACIÓN, 45-50%           [×]  │
│ Solicitud EXP-2026-0142              │ Título · abierta/cerrada             │
│ [EN GESTIÓN] [Alta] [Finalizar]      ├──────────────────────────────────────┤
├───────────────────────────────────────┤ Nombre completo · Asesoría Legal     │
│ RESUMEN EJECUTIVO (refluye)          │ Mensaje y adjuntos...                │
│ fechas │ áreas │ participantes       │                                      │
├───────────────────────────────────────┤ Nombre completo · Centro Médico      │
│ FLUJO OPERATIVO                      │ Respuesta / mención...               │
│ rail global con scroll interno       │                                      │
│ Asesoría Legal │ [Ciclo 1════▶]      │                                      │
│ Centro Médico  │   [Ciclo 1══■]      ├──────────────────────────────────────┤
├───────────────────────────────────────┤ [Responder a...]                     │
│ DETALLE CONTEXTUAL EN PÁGINA         │ [Escribir comentario...] [Enviar]   │
└───────────────────────────────────────┴──────────────────────────────────────┘
```

La apertura cambia las columnas del layout y provoca reflow real. No oscurece, desenfoca, cubre ni bloquea el contenido principal. El grafo conserva su lienzo mínimo y obtiene scroll horizontal interno; la página completa no desborda horizontalmente.

### Mobile, conversación oculta
```text
┌──────────────────────────────┐
│ ‹ Solicitudes               │
│ Solicitud EXP-2026-0142     │
│ [EN GESTIÓN] [Alta]         │
│ [Conversación]              │
├──────────────────────────────┤
│ RESUMEN EJECUTIVO           │
│ Asunto completo             │
│ Registro │ Límite           │
│ Áreas │ Participantes       │
├──────────────────────────────┤
│ FLUJO OPERATIVO             │
│ [Área fija] ← desplazar →   │
│ Estado ●────●────────▷      │
│ Legal  [Ciclo 1══════▶]     │
│ Médico    [Ciclo 1══■]      │
├──────────────────────────────┤
│ Detalle seleccionado        │
└──────────────────────────────┘
```

### Mobile, conversación no modal
```text
Vista Solicitud                    Vista Conversación
┌──────────────────────────────┐   ┌──────────────────────────────┐
│ Solicitud ... [Conversación] │ → │ ‹ Volver a Solicitud        │
│ resumen + grafo              │   │ Conversación · 12 mensajes  │
└──────────────────────────────┘   ├──────────────────────────────┤
                                   │ hilo con nombres y roles     │
                                   │ ...                          │
                                   ├──────────────────────────────┤
                                   │ compositor fijo al final     │
                                   └──────────────────────────────┘
```

En móvil, la conversación es una vista navegable dentro de la ruta o del estado de la página, no una capa superpuesta. `Volver a Solicitud` restaura posición de scroll, elemento seleccionado y escala temporal. El botón Atrás del navegador debe producir el mismo resultado.

## Comportamiento de la conversación
- Escritorio: panel lateral integrado de 45-50% del contenedor; contenido principal de 50-55%.
- El toggle `Conversación` abre y cierra el panel y permanece accesible en el encabezado. Puede indicar conteo o `cerrada` si esos datos ya existen.
- Incluir botón de cierre con nombre accesible `Cerrar conversación`; cerrar no limpia borrador, respuesta objetivo ni selección operativa durante la sesión.
- Permitir redimensionar solo si el sistema actual ya ofrece un componente separador accesible. Sin ese soporte, usar división estable 50/50.
- Mantener hilos, menciones, adjuntos y compositor de `ConversacionPanel`; mostrar nombre completo primero y `Área · rol · Ciclo` como contexto secundario.
- No usar `Sheet`, `Dialog`, `aria-modal`, focus trap, overlay, blur ni backdrop. El foco puede circular entre contenido y conversación.
- Una conversación cerrada sigue siendo consultable; ocultar o bloquear solo el compositor según el comportamiento existente.

## Resumen ejecutivo
### Contenido y jerarquía exactos
1. **Asunto del expediente:** texto principal, hasta dos líneas, antes que cualquier identificador técnico.
2. **Identificación:** `Expediente {id_publico}` y `Solicitud {id_publico}` si ambos existen; estilo monoespaciado secundario.
3. **Estado y prioridad:** etiquetas semánticas `REGISTRADA`, `EN_EN_GESTION` o `FINALIZADA` usando el label de presentación existente; prioridad adyacente pero visualmente secundaria.
4. **Fechas clave:** `Registrada`, `Inicio de gestión`, `Fecha límite`; mostrar `No definida` solo cuando conocer la ausencia sea útil.
5. **Alcance actual:** `Áreas activas`, `Etapas activas`, `Participantes activos`.
6. **Responsabilidad:** `Asesoría Legal · Principal` y áreas adjuntas como `Centro Médico · Adjunta`.
7. **Último movimiento:** estado o evento, fecha/hora, actor por nombre y contexto de rol si existe.

No mostrar avatares de iniciales como identidad principal, UUID, conteos sin etiqueta, historial completo, motivos extensos, participantes retirados ni respuestas completas. El resumen no debe repetir tarjetas de cada área ni usar `Períodos` como título visible.

## Flujo operativo temporal
### Modelo gráfico obligatorio
- El eje X representa tiempo real y compartido por todos los carriles; el eje Y representa áreas.
- Sobre los carriles se ubica un rail global `Estado de la Solicitud` con nodos como `REGISTRADA`, `EN_EN_GESTION` y `FINALIZADA`, anclados a `fecha_cambio`.
- Cada área ocupa una lane: `Asesoría Legal` con insignia `Principal`; `Centro Médico` con `Adjunta`. La etiqueta del área queda fuera del lienzo temporal.
- Cada `Ciclo 1` se representa con una barra cuyo inicio y fin corresponden a `fecha_inicio` y `fecha_fin`.
- Un ciclo abierto termina con borde/flecha abierta y la etiqueta `En curso`; su barra llega hasta el marcador de tiempo actual sin sugerir cierre.
- Los eventos son nodos anclados a su `timestamp`: cambio de estado, alta/retiro de participante, respuesta de conformidad u observación y cierre.
- Conectores sólidos unen estados del mismo ciclo; conectores verticales finos relacionan un cambio global con eventos de área cuando comparten causalidad disponible. No inventar relaciones si el payload no las expresa.
- Estados: borgoña para activo/en gestión, neutro oscuro para registrado, gris para cerrado/finalizado y rojo de alerta solo para error, rechazo, observación crítica o bloqueo. Añadir forma, borde, icono o texto; nunca depender solo del color.
- Dibujar una línea vertical `Ahora` cuando exista al menos un ciclo abierto y el rango incluya la fecha actual.
- Etiquetas visibles: área, tipo de participación, ciclo, estado y fechas abreviadas. Nombres de actores/roles aparecen en tooltip y detalle, no saturan cada nodo.
- Tooltip al hover/foco: fecha y hora exactas, descripción, actor con nombre, rol/área, estado anterior/nuevo y tipo de respuesta.
- Seleccionar barra o nodo actualiza el panel contextual en página y aplica estado visual seleccionado.

### Escala, colisiones y ausencia de datos
- Calcular rango desde el timestamp mínimo al máximo de rail, ciclos y eventos; añadir margen visual inicial/final.
- Para rangos largos, ofrecer escalas discretas `Días`, `Semanas`, `Meses` solo si son necesarias; elegir automáticamente una densidad legible sin alterar la posición temporal relativa.
- El lienzo tiene ancho mínimo proporcional al rango. Si excede el contenedor, usar scroll horizontal interno y conservar visible la primera y última marca temporal.
- Eventos con el mismo timestamp se apilan perpendicularmente al eje en un clúster numerado; al activar el clúster se despliega una lista breve ordenada por prioridad semántica y orden estable original.
- Si inicio y fin son iguales, representar un hito de duración cero con ancho táctil mínimo, fecha única y texto `Mismo instante`; no falsear duración.
- Si varios ciclos empiezan o terminan en la misma fecha, desplazar etiquetas en niveles alternos y mantener el anclaje mediante una línea guía.
- Si falta una fecha opcional, usar el dato contractual disponible: abierto cuando `fecha_fin` es nula. No ubicar elementos sin timestamp en una fecha inventada; mostrarlos en el detalle como `Fecha no disponible`.
- Si no hay áreas ni eventos, mostrar `Sin datos de trazabilidad` y una explicación breve. Si hay áreas sin etapas, conservar su lane con `Sin etapas registradas`.
- Un feed compacto de eventos puede ser opcional como filtro o resumen de los últimos 3-5 movimientos. Nunca debe dominar ni repetir toda la cronología del grafo.

### Comportamiento móvil del grafo
El grafo mantiene orientación temporal horizontal. El lienzo se desplaza horizontalmente y las etiquetas de áreas permanecen sticky a la izquierda; el rail global también conserva su etiqueta. No convertirlo en lista vertical por defecto. Solo se admite una lista como fallback explícito de accesibilidad o incompatibilidad técnica, activada por control `Ver como lista`, sin reemplazar el grafo para los demás usuarios.

## Detalle contextual seleccionado
Se recomienda **panel en página bajo el grafo**, no drawer lateral. Así el chat puede ocupar el único lateral disponible sin que dos paneles compitan por ancho, foco o jerarquía.

El panel muestra según selección: `Ciclo 1 · Asesoría Legal · Principal`, estado y rango; participantes con nombre, rol y vigencia; historial de estados; respuestas de `Conformidad` u `Observación`; actor de inicio/cierre; motivo y fecha exacta. Un evento muestra descripción, actor, transición y vínculo al ciclo. Incluir `Cerrar detalle` y conservar la posición horizontal del grafo.

En desktop, mantenerlo bajo el grafo dentro de la columna principal. En móvil, ubicarlo inmediatamente después del grafo y desplazarlo a la vista al seleccionar, respetando movimiento reducido. `PeriodDetailContent` puede reutilizarse; `PeriodDetailSheet` deja de ser el contenedor recomendado.

## Política visual de acciones operativas
- Mostrar una acción solo cuando coincidan las condiciones frontend existentes de usuario, área, estado y participación activa; ocultarla en cualquier otro caso.
- Reutilizar `isUserAssignedToArea`, los helpers de estado activo/cerrado y la comprobación de participante activo del período. Mantener la normalización de UUID antes de comparar.
- `Tomar`: visible para miembro del área, ciclo no cerrado/finalizado/cancelado y usuario aún no participante activo.
- Menú operativo: visible únicamente para miembro aplicable o participante activo, con las mismas validaciones de estado usadas por `PeriodoOperacionesMenu`.
- `Finalizar Solicitud`: visible solo si la Solicitud no está `FINALIZADA`/`ANULADA` y `userCanFinalize` es verdadero. No mostrarla deshabilitada a observadores.
- Durante una mutación sí se admite deshabilitar temporalmente el control accionado y mostrar progreso, para evitar envíos dobles.
- Esta política es exclusivamente de presentación UX. **No constituye seguridad ni autorización** y no agrega Guardian, reglas ni restricciones backend en este alcance.

## Vistas por rol
| Vista | Presentación | Acciones |
|---|---|---|
| Administrativa / observadora | Resumen completo, rail global, todos los carriles, eventos, participantes y respuestas; énfasis en estado y auditoría. | Solo acciones globales o contextuales que ya cumplan las condiciones frontend; las demás no se renderizan. |
| Participante operativo | Misma trazabilidad completa, con su área y ciclo activo resaltados sutilmente y `Tu participación` como contexto secundario. | Acciones aplicables al área/ciclo actual más visibles cerca del detalle seleccionado; las no aplicables se ocultan. |

Las diferencias son solo visuales y de ubicación/visibilidad de acciones. No filtrar información contractual ni introducir una política de permisos nueva.

## Sistema visual y composición
- Contenedor: ancho disponible del `PageWrapper`; separación vertical principal de 24 px y separación interna de 16 px.
- Resumen: padding 20-24 px; grid adaptable sin microtarjetas independientes para cada dato.
- Grafo: encabezado a contenido 12-16 px; lanes de 64-88 px según densidad; 8 px entre marcas relacionadas y 16 px entre grupos.
- Tipografía: título de página 24-28 px; asunto 18-20 px semibold; títulos de sección 14 px semibold; cuerpo 14 px; metadatos 12 px. Evitar `font-black` y mayúsculas excesivas en textos operativos.
- Color: borgoña CIP como acento y foco; rojo reservado para riesgo/error; fondo blanco o neutro muy claro; bordes grises; texto principal casi negro y secundario con contraste AA.
- Superficies planas con bordes y sombra mínima. Sin gradientes, glassmorphism, tarjetas KPI genéricas ni decoración que compita con el tiempo.
- Al abrir chat, el resumen pasa a menos columnas y las etiquetas envuelven; el grafo no comprime nodos por debajo del mínimo legible.

## Estados de interacción
- **Carga:** skeleton por secciones: encabezado estable, resumen, rail y 2-3 lanes. Evitar spinner que oculte toda la página.
- **Trazabilidad vacía:** mensaje único, explicación y contenido ejecutivo disponible; no mostrar un contenedor gráfico vacío gigante.
- **Error de API:** conservar resumen si cargó; en flujo mostrar `Error al cargar trazabilidad`, mensaje seguro y botón `Reintentar`.
- **Selección sin acciones aplicables:** mostrar detalle completo sin barra de botones ni texto acusatorio; opcional `Vista de consulta`.
- **Texto largo:** asunto a dos líneas en resumen; observaciones y respuestas completas en detalle con `overflow-wrap:anywhere`; no truncar información crítica sin acceso a expansión.
- **Muchas áreas/eventos:** scroll vertical natural de lanes, horizontal solo dentro del grafo, agrupación de colisiones y virtualización únicamente si el volumen real la exige.
- **Área retirada o ciclo cerrado:** conservarlos en su posición histórica con estilo neutro y fechas de cierre; no ocultarlos. Participante retirado muestra nombre, rol, `Retirado` y vigencia en detalle.
- **Conversación vacía/cerrada/error:** mantener cabecera; explicar estado; ocultar o bloquear compositor según contrato; ofrecer reintento cuando exista soporte actual.

## Accesibilidad
- Usar `button` para toggles, nodos y barras seleccionables; `time` con `dateTime` para fechas; encabezados y regiones con nombres claros.
- Orden de teclado: encabezado y acciones, resumen, controles del grafo, carriles/nodos, detalle contextual y conversación abierta.
- Proveer foco visible borgoña de al menos 2 px y devolver el foco al disparador al cerrar chat o detalle.
- Cada barra anuncia área, `Ciclo`, tipo, estado, inicio, fin/en curso y cantidad de participantes. Cada evento anuncia tipo, fecha y actor.
- El separador redimensionable, si existe, debe operar con teclado, exponer valor/tamaño y tener objetivo mínimo de 44 px táctiles en móvil.
- No usar semántica modal para chat ni detalle en página. Informar cambios de carga/error mediante regiones `status`/`alert` sin mover foco arbitrariamente.
- Garantizar contraste AA, iconos acompañados por texto, estados no codificados solo por color y objetivos interactivos mínimos de 44 x 44 px.
- Con `prefers-reduced-motion`, eliminar desplazamientos animados y usar cambios inmediatos; conservar solo transiciones de color discretas.

## Criterios de aceptación
- [ ] Resumen ejecutivo y flujo operativo aparecen juntos, sin pestañas primarias `Resumen` / `Trazabilidad`.
- [ ] Con chat oculto, el contenido principal usa todo el ancho disponible.
- [ ] En desktop, abrir chat crea split pane integrado 50/50 aproximado y el contenido principal refluye.
- [ ] El chat no usa `Sheet`, modal, overlay, backdrop, blur, portal modal ni focus trap.
- [ ] Cerrar y reabrir chat conserva contexto de página y estado de trabajo durante la sesión.
- [ ] En móvil, chat es una vista navegable no modal con retorno que restaura contexto.
- [ ] El grafo usa X como tiempo compartido e Y como carriles de área.
- [ ] Existe rail global de estado sobre los carriles con `REGISTRADA`, `EN_EN_GESTION` y `FINALIZADA` según datos.
- [ ] Barras de `Ciclo 1` reflejan inicio/fin real y los ciclos abiertos son visualmente abiertos.
- [ ] Eventos se anclan a timestamps y las colisiones simultáneas son operables por teclado y tacto.
- [ ] En móvil, el grafo conserva orientación horizontal, scroll interno y etiquetas sticky de área.
- [ ] Seleccionar ciclo, participante, respuesta o evento abre detalle contextual en página, no un segundo lateral.
- [ ] No existe una lista cronológica larga que duplique el grafo; cualquier feed es breve y secundario.
- [ ] Nombres completos preceden a iniciales; área, rol y ciclo aportan contexto de identidad.
- [ ] Se representan Asesoría Legal (Principal), Centro Médico (Adjunta), participantes y respuestas de conformidad/observación cuando existan.
- [ ] Acciones no aplicables se ocultan; solo la acción en curso puede mostrarse temporalmente deshabilitada.
- [ ] La visibilidad reutiliza `isUserAssignedToArea`, participante activo y estados activos/cerrados existentes.
- [ ] No se introduce autorización, Guardian, reglas ni cambio backend.
- [ ] Carga, vacío, error/reintento, textos largos, gran volumen y ciclos cerrados tienen tratamiento definido.
- [ ] Navegación por teclado, foco, etiquetas, contraste, semántica y movimiento reducido cumplen lo especificado.
- [ ] La estética conserva borgoña/rojo CIP y neutros, sin gradientes ni apariencia de dashboard genérico.

## Entrega de implementación frontend
### Archivos existentes a modificar
- `frontend/src/app/(protected)/solicitudes/[id]/page.tsx`: layout único, estado del split pane, eliminación de tabs primarias y `Sheet` de conversación, composición de acciones.
- `frontend/src/features/tramites/components/SolicitudResumenOperativo.tsx`: jerarquía, labels, responsabilidad y reflow del resumen.
- `frontend/src/features/tramites/components/trazabilidad/TrazabilidadView.tsx`: composición del grafo y selección contextual; retirar timeline larga y `PeriodDetailSheet` como contenedor.
- `frontend/src/features/tramites/components/trazabilidad/TrazabilidadFlowDiagram.tsx`: sustituir composición de tarjetas por lienzo temporal compartido.
- `frontend/src/features/tramites/components/trazabilidad/AreaLane.tsx`: lane temporal, etiqueta sticky y escala común.
- `frontend/src/features/tramites/components/trazabilidad/PeriodNode.tsx`: evolucionar de tarjeta a barra temporal seleccionable.
- `frontend/src/features/tramites/components/trazabilidad/PeriodDetailContent.tsx`: reutilizar contenido dentro del panel contextual en página.
- `frontend/src/features/conversaciones/components/ConversacionPanel.tsx`: adaptación al panel integrado, cabecera/cierre externo y altura responsive.
- `frontend/src/features/conversaciones/components/CommentThread.tsx`: identidad nombre-primero y ajuste a ancho variable, preservando hilos.

### Componentes sugeridos a crear
- `SolicitudWorkspaceLayout.tsx`: contenido principal + conversación integrada; sin primitivas modales.
- `SolicitudTimeGraph.tsx`: escala X compartida, rail global, lanes, marcador actual y gestión de overflow.
- `SolicitudStateRail.tsx`: estados globales y timestamps.
- `AreaTimeLane.tsx`: etiqueta sticky y contenido temporal por área.
- `OperationalSelectionPanel.tsx`: envoltorio en página para `PeriodDetailContent` y acciones aplicables.
- `TimeGraphLegend.tsx`: leyenda semántica compacta y controles de escala.

Los nombres pueden ajustarse a la convención local, pero deben conservar estas responsabilidades. Reutilizar `useSolicitudDetail`, `useSolicitudTrazabilidad`, `ConversacionPanel`, tokens `ESTADO_SOLICITUD`/`PRIORIDAD_SOLICITUD`, hooks de operación y schemas actuales. No modificar backend.

## Plano visual de una página: desktop con conversación y grafo
```text
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Solicitudes / EXP-2026-0142                                                                        │
│ Solicitud EXP-2026-0142  Detalle operativo       [EN GESTIÓN] [Alta] [Finalizar] [Conversación ●]│
├──────────────────────────────────────────────────────────────┬─────────────────────────────────────┤
│ RESUMEN EJECUTIVO                                           │ CONVERSACIÓN                    [×] │
│ Atención médico-legal para expediente presentado            │ Coordinación del trámite             │
│ Expediente EXP-2026-0142                                    │ 12 mensajes · iniciada 12 sep        │
│ Registrada 12 sep │ Inicio 13 sep │ Límite 20 sep           ├─────────────────────────────────────┤
│ 2 áreas activas │ 2 etapas │ 4 participantes               │ María Pérez                         │
│ Principal: Asesoría Legal │ Adjunta: Centro Médico          │ Asesoría Legal · Asesora · Ciclo 1  │
│ Último movimiento: conformidad registrada · 15 sep 10:30    │ Se revisó el sustento...             │
├──────────────────────────────────────────────────────────────┤                                     │
│ FLUJO OPERATIVO                         [Días] [Leyenda]     │ Carlos Ramos                        │
│                                                              │ Centro Médico · Médico · Ciclo 1     │
│                 12 sep       13 sep       15 sep      Ahora  │ Remito respuesta de conformidad...  │
│ Estado Solicitud ● REGISTRADA──● EN_EN_GESTION─────────┆    │ [adjunto.pdf]                       │
│ ─────────────────────────────────────────────────────────┆── │                                     │
│ Asesoría Legal  Principal │ [Ciclo 1════════════════════▶┆] │ Sistema                             │
│                           │  ● alta     ● observación     ┆  │ Estado: REGISTRADA → EN_EN_GESTION │
│ Centro Médico   Adjunta   │    [Ciclo 1══════════■]      ┆  │                                     │
│                           │       ● participante ● conform.  │                                     │
│                           └──────────────────────── tiempo → │                                     │
│            ← desplazamiento horizontal interno del grafo →  ├─────────────────────────────────────┤
├──────────────────────────────────────────────────────────────┤ Responder a Carlos Ramos             │
│ DETALLE SELECCIONADO                                         │ [Escribir comentario o @mencionar]  │
│ Ciclo 1 · Centro Médico · Adjunta               [Cerrar]    │ [Adjuntar]                  [Enviar]│
│ FINALIZADA │ 13-15 sep │ Inició: Ana Torres                 │                                     │
│ Respuesta: Conformidad · Carlos Ramos · 15 sep 10:30         │                                     │
│ Participantes: Carlos Ramos (Médico, retirado) · Ana Torres  │                                     │
└──────────────────────────────────────────────────────────────┴─────────────────────────────────────┘
```
