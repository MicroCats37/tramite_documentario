# Auditoría y handoff de implementación: trazabilidad de Solicitud

## A. Veredicto ejecutivo

La implementación post-librerías no debe pulirse de forma incremental: debe corregirse su modelo de visualización. El calendario sí es una base válida para responder **cuándo ocurrió, cuánto duró y qué áreas trabajaron en paralelo**, pero hoy conserva navegación no acotada, cabeceras y densidad por defecto, y no explica bien los datos. El React Flow actual responde únicamente por un ciclo seleccionado, ordena eventos por categoría en vez de por cronología real, pierde sincronización al cambiar de ciclo y no puede dibujar sus aristas porque sus nodos personalizados no tienen `Handle`.

La sustitución requerida mantiene ambas librerías, pero cambia la composición: **calendario global controlado + flujo global de toda la Solicitud + un solo inspector compacto + acciones dentro del contexto del ciclo + chat integrado no modal**. El calendario y el flujo deben compartir selección; ninguno debe reemplazar al otro.

## B. Mapa de arquitectura actual y por qué falla

| Paso actual | Fuente | Resultado actual | Falla estructural |
|---|---|---|---|
| Calendario de Solicitud | `SolicitudTimelineView.tsx:281-590` | Muestra estados puntuales y barras de ciclos por área. | Usa rango inicial no controlado, estilos/cabeceras por defecto y metadatos mínimos. |
| Selección de una barra | `TrazabilidadView.tsx:142-160` | Guarda `flowArea` y `flowPeriod`. | La selección cambia el universo del grafo en vez de enfocar una rama del universo global. |
| Flujo del ciclo seleccionado | `TrazabilidadView.tsx:263-293`; `SolicitudProcessFlow.tsx:684-707` | Construye un flujo con un área y un período. | Omite registro, estado global, otras áreas, otros ciclos, paralelismo y convergencia final. |
| Inspector de nodo | `TrazabilidadView.tsx:283-291`; `ProcessInspector.tsx:315-364` | Muestra resumen del nodo y puede expandir el ciclo completo. | Duplica el detalle del panel operacional y vuelve a crecer hasta una ficha extensa. |
| Panel de selección | `TrazabilidadView.tsx:295-308`; `OperationalSelectionPanel.tsx:159-218` | Renderiza nuevamente `PeriodDetailContent` y acciones. | Conviven dos inspectores para una misma selección, con cierres y jerarquías diferentes. |
| Chat | `SolicitudWorkspaceLayout.tsx:38-80` | Ocupa 45-50 % en escritorio y sustituye la vista en móvil. | El contrato general es correcto, pero calendario, grafo e inspector no adaptan su viewport al ancho reducido. |

La causa de fondo es que `selection`, `flowPeriod`, `flowArea`, `flowNodeId` y `flowNodeData` representan estados paralelos de una misma intención (`TrazabilidadView.tsx:128-140`). Esa duplicación permite que calendario, grafo e inspectores diverjan.

## C. Hallazgos priorizados

| ID | Severidad | Síntoma observado | Ubicación exacta | Causa técnica | Impacto UX | Corrección obligatoria |
|---|---|---|---|---|---|---|
| F01 | Crítica | No se ven conexiones entre nodos. | `SolicitudProcessFlow.tsx:20-29`, `172-197`, `237-445`, `482-489` | Se crean aristas con IDs válidos, pero no se importa ni renderiza `Handle` en ningún nodo personalizado. | El flujo parece una colección de tarjetas sueltas; se pierde la secuencia. | Cada nodo conectable debe exponer `Handle` de entrada a la izquierda y salida a la derecha, con excepciones explícitas para inicio/terminal; las aristas deben referenciar nodos y, si se nombran, handles existentes. |
| F02 | Crítica | React Flow solo muestra un ciclo seleccionado. | `SolicitudProcessFlow.tsx:461-476`, `684-703`; `TrazabilidadView.tsx:132-160`, `263-281` | El constructor recibe exclusivamente `area` y `period`; el grafo solo se monta cuando ambos existen. | No responde cómo toda la Solicitud llegó a su conclusión. | El constructor debe recibir la trazabilidad completa y el contexto global de la Solicitud; la selección solo resalta y centra una rama. |
| F03 | Crítica | Al elegir otro ciclo, encabezado y grafo pueden quedar desincronizados. | `SolicitudProcessFlow.tsx:701-712` | `useNodesState(initialNodes)` y `useEdgesState(initialEdges)` consumen el valor inicial una vez; el `useEffect` destinado a sincronizar no hace nada. | Puede mostrarse el título del nuevo ciclo con nodos/aristas del anterior. | Derivar nodos/aristas del modelo global de forma controlada o sincronizarlos explícitamente; la selección debe modificar `selected`, no reconstruir un flujo parcial. |
| F04 | Crítica | La supuesta secuencia cronológica puede ser falsa. | `SolicitudProcessFlow.tsx:537-630` | Se agregan primero todos los participantes, después todos los estados y finalmente todas las respuestas; solo se ordena dentro de cada categoría. | Una respuesta anterior puede aparecer después de un cambio posterior y las aristas comunican una secuencia incorrecta. | Crear eventos normalizados, ordenarlos globalmente por timestamp y usar aristas cronológicas solo donde corresponda; no declarar causalidad sin dato backend. |
| F05 | Alta | Nodos diminutos, gran vacío y lienzo excesivo. | `SolicitudProcessFlow.tsx:107-127`, `777-795` | Seis tracks fijos separados 200 px producen 1240 px de alto; cada evento avanza 300 px en X y `fitView` intenta abarcar todo. | Lectura imposible y desperdicio vertical. | Sustituir tracks fijos por layout jerárquico agrupado; limitar alto y permitir pan interno a zoom legible. |
| F06 | Alta | El usuario puede alejar hasta volver ilegibles los nodos. | `SolicitudProcessFlow.tsx:793-806` | `minZoom={0.1}`, zoom por scroll activo y control de ajuste sin política de legibilidad. | El grafo deja de ser auditable. | Usar zoom mínimo legible dinámico, nunca menor a 0.75 como referencia; impedir que `fitView` y el botón de ajuste lo vulneren. |
| F07 | Alta | El calendario puede desplazarse y ampliarse fuera de la vida real del trámite. | `SolicitudTimelineView.tsx:412-418`, `460-476` | Solo usa `defaultTimeStart/defaultTimeEnd`; no existen estado controlado, `visibleTimeStart/End` ni `onTimeChange` con clamp. | El usuario termina en tiempo vacío y pierde el contexto. | Controlar el intervalo, acotar pan/zoom a límites de datos con padding pequeño y ofrecer `Ajustar al trámite`. |
| F08 | Alta | Una Solicitud cerrada puede extenderse artificialmente hasta hoy. | `SolicitudTimelineView.tsx:118-168` | `max` se calcula con `Math.max(...points, now)` incluso sin períodos abiertos; la condición posterior ya no puede deshacerlo. | La duración visual comunica meses o años inexistentes. | Incluir `now` únicamente si existe período abierto o estado global vigente; para cerrada usar último evento real/`fecha_cierre`. |
| F09 | Alta | Cabecera roja genérica y fechas inglesas recortadas. | `SolicitudTimelineView.tsx:16-23`, `446-478`; `node_modules/react-calendar-timeline/dist/Timeline.scss:14-20`, `139-162` | Se importa el CSS de fábrica, cuya raíz usa `#c52020`, y no se renderizan `TimelineHeaders`/`DateHeader` personalizados ni formato `es-PE`. | Aspecto ajeno al sistema, texto truncado y escala difícil de leer. | Crear cabeceras propias en español, con unidades adaptativas, ancho suficiente y estilos semánticos CIP; sobrescribir explícitamente la raíz/cabeceras del paquete. |
| F10 | Alta | La fila de estado representa mal los estados. | `SolicitudTimelineView.tsx:323-345`, `177-221` | Cada estado tiene inicio y fin idénticos y se intenta dibujar como círculo dentro de un ítem de ancho cero. | No se entiende cuánto permaneció la Solicitud en cada estado; algunos puntos pueden desaparecer. | Convertir cambios globales en segmentos desde cada cambio hasta el siguiente o cierre/ahora, con etiqueta humanizada; conservar hitos como marcadores separados. |
| F11 | Alta | No se comunica duración, responsabilidad ni contexto suficiente por área. | `SolicitudTimelineView.tsx:294-312`, `347-383`, `226-264` | La barra solo dice ciclo + enum; el sidebar solo muestra nombre y tipo actual. | El usuario debe inferir duración, ciclos, estado reciente y responsables. | Mostrar duración explícita, total de ciclos, último estado y participantes/responsabilidad disponibles, sin inventar campos ausentes. |
| F12 | Alta | Dos paneles detallan lo mismo y ambos pueden ser grandes. | `TrazabilidadView.tsx:283-308`; `ProcessInspector.tsx:261-304`, `315-364`; `OperationalSelectionPanel.tsx:159-218` | `ProcessInspector` expande `PeriodDetailContent` y `OperationalSelectionPanel` lo renderiza completo simultáneamente. | Duplicación, scroll largo y competencia con el chat. | Eliminar la composición duplicada y mantener un único inspector compacto con niveles de revelado y un solo pie de acciones. |
| F13 | Alta | El resumen muestra ceros activos junto con áreas responsables sin explicar el histórico. | `SolicitudResumenEjecutivo.tsx:62-91`, `198-218`, `221-258` | Solo calcula activos, mientras la responsabilidad recorre todas las asignaciones; además toma el tipo del primer período y cae a `ADJUNTA`. | Una Solicitud finalizada parece contradictoria o mal cargada. | Mostrar activos y totales/históricos juntos y derivar responsabilidad actual de `tipo_actual` de trazabilidad cuando esté disponible. |
| F14 | Media | Estados y tipos aparecen como enums crudos. | `SolicitudTimelineView.tsx:328-336`, `358-363`; `SolicitudProcessFlow.tsx:362-370`, `584-620`, `740-744`; `PeriodDetailContent.tsx:77-108`, `214-278`, `407-456`; `ProcessInspector.tsx:163-212` | Los schemas aceptan `string` y cada vista imprime el valor sin humanizador común. | Etiquetas como `AREA_INCORPORADA`, `EN_GESTION` u `OBSERVACION` aumentan carga cognitiva. | Centralizar labels en español para estado global, estado de ciclo, tipo de evento, participación, cierre y respuesta; fallback legible, nunca snake case visible. |
| F15 | Media | Marcadores saturan el calendario y no se pueden inspeccionar. | `SolicitudTimelineView.tsx:387-408`, `522-555`, `422-438` | Se crea una línea por cada evento, sin etiqueta; claves basadas solo en timestamp pueden colisionar y estados son no-op al seleccionar. | Ruido visual sin trazabilidad accionable. | Reservar marcadores para hitos relevantes, usar ID estable compuesto y hacer seleccionables estados/eventos con tooltip e inspector. |
| F16 | Media | El contexto “mi responsabilidad” está declarado pero no existe. | `SolicitudTimelineView.tsx:268-289`, `294-312` | `currentUserId` y `userAreaIds` se renombran con `_` y nunca se usan. | No se distingue dónde participa el usuario ni con qué rol. | Usar datos reales para una señal secundaria “Tu participación”; nombre completo, rol y área siguen siendo la identidad principal. |
| F17 | Media | Las acciones operativas aparecen en más de un lugar y su dueño visual no es único. | `OperationalSelectionPanel.tsx:87-155`; `page.tsx:412-555` | La página mantiene acciones por período y el panel contextual agrega otro pie para la misma entidad. | Controles repetidos y riesgo de estados de carga divergentes. | Mantener acciones en el inspector del ciclo seleccionado; la sección histórica inferior debe quedar informativa o reutilizar exactamente el mismo componente/estado. |
| F18 | Media | Al abrir chat, el grafo se comprime sin política específica. | `SolicitudWorkspaceLayout.tsx:38-80`; `page.tsx:301-329` | El layout divide 55/45, pero los visualizadores no reciben el cambio de modo ni fijan ancho interno legible. | `fitView` vuelve a reducir nodos y el inspector compite por espacio vertical. | Observar resize, conservar escala mínima, usar pan/scroll interno y compactar el inspector; bajo 1024 px mantener la navegación no modal actual. |
| F19 | Media | Tipado y accesibilidad prometen más de lo implementado. | `SolicitudTimelineView.tsx:70-88`, `446-452`; `SolicitudProcessFlow.tsx:797-806` | Dos casts `any` ocultan el contrato del renderer; el texto ARIA indica navegación/selección sin etiquetas específicas por nodo ni contrato visible de foco. | Regresiones silenciosas y navegación asistiva ambigua. | Tipar renderers desde `ReactCalendarTimelineProps`, definir `aria-label` por nodo, foco visible, orden lógico y alternativa textual resumida. |

**Conteo:** 4 críticas, 9 altas y 6 medias; 19 hallazgos en total.

## D. Auditoría detallada de `react-calendar-timeline`

### Evidencia de librería y tipos locales

| Evidencia | Confirmación |
|---|---|
| Versión instalada | `react-calendar-timeline@0.30.0-beta.4`, confirmada por `package.json:36`, `package-lock.json:7628-7644` y `npm list`. |
| Rango controlado | Los tipos locales exponen `visibleTimeStart`, `visibleTimeEnd` y `onTimeChange` en `node_modules/react-calendar-timeline/dist/lib/Timeline.d.ts:15-24`, `66`. |
| Densidad | Los tipos exponen `lineHeight`, `itemHeightRatio` e `itemVerticalGap` en `Timeline.d.ts:32-39`. |
| Cabeceras | El paquete exporta `TimelineHeaders` y `DateHeader` en `dist/index.d.ts:8-15`; `DateHeader` acepta `labelFormat` y `height` en `dist/lib/headers/DateHeader.d.ts:6-27`. |
| Renderer de grupo | Sí está exportado por `export *` en `dist/index.d.ts:17` y definido en `dist/lib/types/main.d.ts:90-93`. El comentario de aplicación que afirma lo contrario es inexacto. |
| Renderer de ítem | No hay export nombrado `ItemRendererProps`; debe derivarse de `ReactCalendarTimelineProps<RctItem, RctGroup>["itemRenderer"]` en lugar de mantener un contrato parcial y forzar `any`. |

### Diagnóstico actual

- El rango calculado en `buildVisibleRange` es razonable como intención, pero incorrecto para Solicitudes cerradas por la inclusión incondicional de `now`.
- `defaultTimeStart/defaultTimeEnd` solo establecen la primera vista. La librería conserva un canvas navegable y el usuario puede salir del dominio de datos.
- `minZoom` y `maxZoom` actuales limitan tamaño de ventana, no los límites temporales. `maxZoom` de dos años permite una escala donde horas/días reales dejan de ser útiles.
- La cabecera visible es la cabecera automática del paquete. Su SCSS define la raíz roja en `Timeline.scss:14-20`, `158-162`; no existe override local según la búsqueda de clases `rct-*`.
- No se fijan `lineHeight`, `itemHeightRatio` ni `itemVerticalGap`, por lo que la densidad visual queda en defaults no diseñados para esta ficha.
- El sidebar de 168 px (`SolicitudTimelineView.tsx:465`) fuerza truncado de áreas y no ofrece resumen operativo.
- Todos los eventos se convierten en líneas verticales tenues; esto no distingue hito global, respuesta, participante o cambio interno.
- `title` de ciclos y estados conserva enums crudos y no incluye duración.

### Reemplazo requerido

1. Calcular `dataStart` como el mínimo real entre registro de Solicitud, historial global, incorporación de área, inicio/fin de ciclos y timeline.
2. Calcular `dataEnd` como último instante real para una Solicitud cerrada; usar `now` solo si existe ciclo abierto o estado global activo.
3. Aplicar padding pequeño y determinista: 3-5 % del ciclo de vida, con piso útil para trámites de horas y techo de pocos días para trámites largos.
4. Mantener `visibleTimeStart/visibleTimeEnd` en estado controlado.
5. En `onTimeChange`, conservar la duración solicitada, desplazarla dentro de `[minBound, maxBound]`, llamar `updateScrollCanvas` y actualizar estado.
6. Hacer que el zoom máximo visible sea el rango de datos con padding; el usuario nunca debe alejarse a años vacíos.
7. Agregar botón persistente `Ajustar al trámite`, que restaura exactamente el rango inicial derivado de datos.
8. Renderizar `TimelineHeaders` con cabecera primaria y secundaria en español; elegir mes/semana/día/hora según amplitud y ancho, sin textos como `Saturday, September...`.
9. Sustituir fondo rojo por superficies CIP neutras, bordes del sistema y texto con contraste AA; reservar borgoña para estado/selección, no para toda la cabecera.
10. Usar filas de 64-72 px y barras de 30-36 px en escritorio; permitir 72-80 px cuando el sidebar tenga tres líneas de contexto.
11. Ampliar sidebar a 240-280 px en vista completa y mantener un ancho legible fijo cuando el chat reduzca el panel.
12. En cada área mostrar: nombre, `Principal`/`Adjunta`, `N ciclos`, último estado humanizado y participante responsable si el payload lo permite.
13. Mostrar en cada barra `Ciclo N`, tipo, duración legible y estado; tooltip con fechas exactas y participante(s), sin afirmar un responsable si solo existe una lista histórica.
14. Representar estado global como segmentos de duración entre transiciones. Los puntos quedan para hitos, no para sustituir el estado sostenido.
15. Usar marcadores solo para registro, cambios globales relevantes, respuestas y `Ahora` cuando corresponda; cada uno debe ser seleccionable y describible.

## E. Auditoría detallada de React Flow

### Diagnóstico exacto de aristas y `Handle`

- Los endpoints lógicos son válidos. `addEdge` asigna `source` y `target` recibidos (`SolicitudProcessFlow.tsx:482-489`), y cada llamada usa `lastNodeId` y el ID de un nodo recién creado (`533-535`, `563-565`, `595-597`, `627-629`, `652-653`).
- No se usan `sourceHandle` ni `targetHandle`; esto sería válido si cada nodo tuviera un único handle de cada tipo.
- El fallo confirmado es geométrico: el import de `@xyflow/react` no incluye `Handle` ni `Position` (`20-29`) y `ProcessNodeWrapper` no los renderiza (`172-197`). Ninguno de los siete nodos agrega handles (`237-445`).
- Los tipos instalados documentan que `Handle` define puntos de conexión y muestran target izquierdo/source derecho en `node_modules/@xyflow/react/dist/esm/components/Handle/index.d.ts:11-38`.
- `nodesConnectable={false}` impide edición; no crea ni reemplaza handles. Debe mantenerse por ser un grafo de solo lectura.

### Diagnóstico de escala y layout

- La altura no es 420 px: la fórmula produce `6 × (80 + 120) + 40 = 1240 px` (`SolicitudProcessFlow.tsx:692`, `778-784`).
- El layout separa tipos de evento en tracks, no ramas por área. Tampoco agrupa ciclos ni representa convergencia.
- El eje X avanza 300 px por nodo (`107-124`). Con muchos eventos, el bounding box crece linealmente aunque exista espacio vertical reutilizable.
- `fitView` intenta encajar todo ese bounding box con padding 0.3 y puede llegar a 10 % (`793-796`); el resultado esperado son nodos diminutos y mucho vacío.
- El estado inicial de React Flow ignora cambios posteriores de props y selección (`701-712`).
- Los iconos emoji y textos de 10 px (`237-445`) pierden consistencia y legibilidad al escalar.

## F. Arquitectura objetivo y mapeo del flujo global

### Contrato de datos de entrada

`SolicitudProcessFlow` debe recibir la raíz completa `SolicitudTrazabilidad` y un contexto mínimo proveniente de `SolicitudDetail`: `fecha_registro`, `fecha_cierre`, `estado` e identificador público. Esto no exige backend nuevo: `page.tsx:319-329` ya dispone de `item` y puede pasar ese contexto. El esquema de trazabilidad actual contiene historial, áreas y timeline (`trazabilidad.schema.ts:115-166`), pero no contiene por sí solo el estado/fechas raíz.

### Nodos y agrupación

| Nivel | Nodo/grupo objetivo | Datos reales usados | Regla |
|---|---|---|---|
| Global | Inicio: `Solicitud registrada` | `SolicitudDetail.fecha_registro` | Único nodo de inicio. |
| Global | Estados de Solicitud | `historial_estados` | Orden temporal; label humanizado, actor y observación en inspector. |
| Bifurcación | `Área incorporada` | `areas[].fecha_incorporacion`, nombre, actor, observación | Abre una rama por área desde el evento global cronológicamente compatible. |
| Área | Grupo/swimlane | `area_id`, nombre, `tipo_actual`, `bloquea_cierre` | Un contenedor visual por área, no un track por tipo de evento. |
| Área | Ciclo/período | `areas[].etapas[]` | Subgrupo por `Ciclo N`, ordenado por fechas; mantiene Principal/Adjunta del ciclo. |
| Ciclo | Inicio | `fecha_inicio`, `iniciado_por_nombres` | Entrada del subflujo. |
| Ciclo | Participante agregado | `participantes[].fecha_inicio`, nombre, rol, asignado por | Identidad: nombre completo primero; rol y área como contexto. |
| Ciclo | Participante retirado | `fecha_fin`, retirado por, motivo | Solo si hay fecha/registro real de retiro. |
| Ciclo | Cambio de estado | `historial_estados[]` | Estado anterior/nuevo humanizado, actor, fecha y motivo. |
| Ciclo | Respuesta | `respuestas[]` | Distinguir `Conformidad`, `Observación`, informe, descargo u otro con label humano. |
| Ciclo | Terminal de rama | `fecha_fin`, `tipo_cierre`, `motivo_cierre` | `Ciclo cerrado` o `En curso`; no inventar cierre. |
| Área | Terminal de área | Último ciclo/estado real | Resume rama completada, activa o bloqueante. |
| Global | Convergencia | Terminales de áreas | Nodo de unión visual que no implica aprobación causal. |
| Global | Estado final/actual | `SolicitudDetail.estado`, `fecha_cierre` o último cambio | `Finalizada`, `Anulada` o `Estado actual`; terminal único. |

Las aristas dentro de una colección ordenada pueden expresar **precedencia cronológica**, no causalidad. La incorporación de un área, una respuesta y un cambio global no deben conectarse como causa-efecto salvo que el backend entregue una relación causal explícita. Etiquetar la leyenda: “Las conexiones muestran recorrido y precedencia registrada; no prueban causalidad”.

## G. Contrato exacto de interacción

| Acción | Calendario | Flujo global | Inspector único | Acciones | Chat |
|---|---|---|---|---|---|
| Carga inicial | Ajustado al ciclo de vida. | Visible completo a escala legible, comenzando por registro/primeras ramas. | Cerrado. | Ocultas. | Conserva estado cerrado/abierto de página. |
| Clic en barra de ciclo | Selecciona barra. | Resalta rama de área y subgrafo del ciclo; centra sin reconstruir. | Abre resumen compacto del ciclo. | Muestra solo acciones aplicables al ciclo. | No se cierra. |
| Clic en estado/hito | Resalta hito. | Resalta nodo equivalente si existe. | Muestra fecha, actor, transición y observación. | No muestra acciones de ciclo salvo vínculo explícito. | No se cierra. |
| Clic en nodo React Flow | Mantiene contexto temporal y resalta ítem relacionado. | Marca nodo con foco visible. | Abre resumen del nodo. | Se muestran solo si el nodo pertenece a ciclo operable. | No se cierra. |
| `Ver ciclo completo` | Sin cambio. | Conserva foco. | Expande secciones internas dentro del mismo inspector. | Pie fijo al final del inspector, no duplicado. | No compite por rail lateral. |
| Cerrar inspector | Conserva rango. | Quita selección, no oculta el grafo. | Cierra y devuelve foco al disparador. | Se ocultan. | Sin cambio. |
| `Ajustar al trámite` | Restaura rango de datos. | Sin cambio. | Sin cambio. | Sin cambio. | Sin cambio. |
| `Ajustar flujo` | Sin cambio. | Vuelve al inicio legible o rama seleccionada; jamás reduce bajo mínimo. | Sin cambio. | Sin cambio. | Sin cambio. |

Debe existir una sola selección discriminada con IDs estables (`global-state`, `area`, `period`, `participant-event`, `response`). El componente resuelve desde esos IDs los datos para calendario, grafo e inspector; no mantiene copias `flowArea/flowPeriod/flowNodeData` independientes.

## H. Reglas de viewport y layout

### Motor recomendado

**Recomendación: ELK mediante `elkjs`, con dirección izquierda-derecha y compound nodes para áreas/ciclos.** Agregarlo está justificado porque el objetivo incluye ramas paralelas, grupos anidados, múltiples entradas/salidas y convergencia; el layout determinista actual no escala a esa topología. Dagre es más liviano, pero no resuelve bien compound/swimlane layout ni control de puertos. Un layout determinista artesanal sería aceptable solo para un flujo lineal; aquí acumularía reglas frágiles de colisión.

No instalar ELK durante esta auditoría. La incorporación de dependencia debe ser un work unit separado, revisable y acompañado de una función pura `traceability -> layouted nodes/edges`.

### Política de viewport

- Nodos mínimos: 220-240 px de ancho, 88-104 px de alto; texto principal mínimo 12-13 px y metadatos mínimo 11 px a zoom base.
- Canvas: 480-640 px de alto en escritorio; máximo aproximado de 70 vh. En ancho reducido/chat abierto: 420-560 px. Nunca derivar el alto sumando todas las lanes.
- Escala inicial: 0.85-1 cuando quepa; piso recomendado 0.75. Si el grafo completo no cabe a 0.75, mostrar una porción y permitir pan: NO reducir más.
- `minZoom`: igual al piso legible/zoom inicial permitido; referencia 0.75, no 0.1. `maxZoom`: 1.5-1.75.
- `fitViewOptions`: padding pequeño, `minZoom` y `maxZoom` coherentes con la política. “Ajustar” no significa obligatoriamente mostrar cada nodo simultáneamente.
- Desactivar zoom accidental por rueda en escritorio; usar rueda/trackpad para pan, pinch para zoom táctil y controles explícitos `+`, `−`, `Ajustar`.
- Deshabilitar `−` al alcanzar `minZoom`; no permitir doble clic para alejar/acercar inadvertidamente.
- Definir `translateExtent` alrededor del bounding box ELK con margen de 80-160 px para evitar canvas infinito.
- Centrar selección con `fitBounds`/`setCenter` sobre rama o subgrafo, manteniendo el zoom actual dentro de límites; no ejecutar `fitView` global en cada clic.
- Recalcular layout solo cuando cambian datos estructurales. Un `ResizeObserver` ajusta viewport al contenedor sin recalcular topología.
- En split 55/45 del chat, conservar dimensiones de nodos y habilitar pan horizontal/vertical. No encoger nodos ni abrir un segundo rail para inspector.

## I. Reglas objetivo del timeline

- **Pregunta que responde:** cuándo ocurrió cada ciclo, cuánto duró y qué áreas operaron en paralelo.
- Rango inicial y límites provienen de eventos reales; padding controlado y `now` solo para trabajo abierto.
- `visibleTimeStart/visibleTimeEnd` son controlados; `onTimeChange` clamp-ea navegación y zoom.
- `Ajustar al trámite` siempre visible, con etiqueta, no solo icono.
- Cabeceras en `es-PE`; formatos cortos según ancho: `sep 2026`, `lun 14`, `14 sep`, `09:00`.
- La cabecera no usa rojo sólido. Debe integrarse con `bg-card`, `muted`, bordes y color de texto del sistema.
- Las horas no dominan una Solicitud de varios días/semanas; la unidad secundaria se elige según ventana visible.
- Grupo global: segmentos de estado humanizado. Grupos de área: nombre + tipo + ciclos + estado reciente + responsabilidad disponible.
- Ítems de ciclo: barra de duración con fecha inicial/final o `En curso`, duración humana y estado.
- Concurrencia: áreas en carriles simultáneos y alineados sobre el mismo eje; no serializar ciclos paralelos.
- Marcadores: registro, cambios globales, respuestas/hitos relevantes y `Ahora` si está dentro del dominio abierto.
- Ítems son de solo lectura: sin mover, redimensionar ni cambiar de grupo; selección sí habilitada.
- Escritorio: filas 64-72 px, sidebar 240-280 px. Chat abierto: conservar ancho interno mínimo y scroll horizontal.
- Móvil: no comprimir a miniatura. Mantener canvas mínimo cercano a 760 px, sidebar legible y desplazamiento horizontal interno con indicación de gesto.

## J. Jerarquía del inspector compacto

| Nivel | Contenido | Regla |
|---|---|---|
| 1. Encabezado | Tipo humano, título principal, estado, cerrar. | Una línea principal; nombre completo antes que iniciales/icono. |
| 2. Contexto inmediato | Fecha/hora, área, ciclo, Principal/Adjunta, actor o participante + rol. | Solo campos presentes. No rellenar “responsable” por inferencia. |
| 3. Resumen | Cambio anterior→nuevo, duración, respuesta o motivo, según nodo. | Máximo 3-5 filas visibles. |
| 4. Revelado | `Ver ciclo completo` / `Ver historial` / `Ver respuesta`. | Expande una sección a la vez dentro del mismo contenedor. |
| 5. Acciones | `Tomar` y menú de operaciones existentes. | Solo para ciclo operable y usuario elegible según helpers actuales. |

Eliminar `OperationalSelectionPanel` como panel paralelo o convertirlo en el único `TraceabilityInspector`; eliminar la expansión duplicada de `ProcessInspector`. `PeriodDetailContent` puede reutilizarse tras dividirlo en secciones compactas, pero no debe montarse completo dos veces. Los helpers de `actionVisibility.ts:8-48` se conservan como gating de presentación, explícitamente no como autorización.

## K. Corrección del resumen ejecutivo

| Métrica actual | Reemplazo |
|---|---|
| `Áreas activas: 0` | `0 activas · 2 involucradas` |
| `Etapas activas: 0` | `2 cerradas · 2 totales` o `0 abiertas · 2 totales` |
| `Participantes activos: 0` | `0 activos · N históricos` |

- Contar áreas involucradas por asignación única.
- Contar ciclos abiertos/cerrados/totales desde trazabilidad; usar “ciclos”, no alternar con “etapas”.
- Contar participantes activos e históricos por usuario dentro de ciclos, deduplicando solo para la métrica de personas; conservar eventos repetidos en auditoría.
- Para una Solicitud finalizada, los ceros activos son correctos, pero deben aparecer junto al total histórico.
- Derivar Principal/Adjunta de `area.tipo_actual` cuando esté disponible; no asumir `ADJUNTA` ni usar siempre el primer período (`SolicitudResumenEjecutivo.tsx:82-91`).
- Mantener último movimiento humanizado con fecha y actor.

## L. Requisitos responsive y de accesibilidad

- Todas las selecciones deben ser accesibles con teclado, foco visible y retorno de foco al cerrar inspector.
- Cada nodo necesita `aria-label` autocontenido: tipo, nombre/estado, área/ciclo y fecha esencial.
- Proveer resumen textual del grafo por áreas para lectores de pantalla; el canvas no puede ser la única representación.
- Color no es la única señal: texto, forma/icono consistente, borde y estado escrito.
- Contraste mínimo WCAG AA; no usar texto de 10 px como información crítica.
- Tooltips deben funcionar con hover y foco, no solo puntero.
- Respetar `prefers-reduced-motion` en centrar, pan y transiciones.
- Con chat abierto en escritorio, contenido 50-55 % y chat 45-50 %; el inspector permanece debajo del grafo dentro del contenido, no como tercer panel.
- Al estrecharse el viewport, primero activar pan/scroll interno; debajo de 1024 px, conservar la navegación actual a chat de ancho completo con `Volver a Solicitud` (`SolicitudWorkspaceLayout.tsx:49-80`).
- La página no debe adquirir overflow horizontal; solo los canvases pueden desplazarse internamente.
- Controles de zoom y ajuste deben tener nombre accesible, estado disabled y objetivo táctil mínimo de 44 px.

## M. Archivos a modificar, crear o eliminar

| Acción | Archivo | Alcance |
|---|---|---|
| Modificar | `frontend/src/features/tramites/components/trazabilidad/SolicitudTimelineView.tsx` | Rango controlado, headers, grupos, segmentos, duración, clamp y reset. |
| Reescribir | `frontend/src/features/tramites/components/trazabilidad/SolicitudProcessFlow.tsx` | Grafo global, handles, nodos globales/área/ciclo, ELK, viewport acotado. |
| Modificar | `frontend/src/features/tramites/components/trazabilidad/TrazabilidadView.tsx` | Selección única y sincronización calendario-flujo-inspector. |
| Consolidar | `frontend/src/features/tramites/components/trazabilidad/ProcessInspector.tsx` | Convertirlo en inspector único compacto o reemplazarlo por `TraceabilityInspector.tsx`. |
| Eliminar o absorber | `frontend/src/features/tramites/components/trazabilidad/OperationalSelectionPanel.tsx` | No debe sobrevivir como segundo panel. |
| Refactorizar | `frontend/src/features/tramites/components/trazabilidad/PeriodDetailContent.tsx` | Extraer secciones reutilizables y humanizadas; evitar ficha monolítica duplicada. |
| Modificar | `frontend/src/features/tramites/components/SolicitudResumenEjecutivo.tsx` | Activos + históricos/totales y responsabilidad correcta. |
| Modificar | `frontend/src/features/tramites/components/SolicitudWorkspaceLayout.tsx` | Exponer modo/ancho o atributo de layout para adaptación de canvases, sin modalizar chat. |
| Modificar | `frontend/src/app/(protected)/solicitudes/[id]/page.tsx` | Pasar contexto global, retirar acciones visualmente duplicadas si el inspector es su dueño. |
| Crear | `frontend/src/features/tramites/components/trazabilidad/buildSolicitudFlow.ts` | Normalización pura, IDs, edges cronológicas y datos de layout. |
| Crear | `frontend/src/features/tramites/components/trazabilidad/traceabilityLabels.ts` | Humanizadores de enums con fallback seguro. |
| Crear | `frontend/src/features/tramites/components/trazabilidad/traceabilityTimeline.ts` | Rango/límites, segmentos de estado y duración. |
| Crear | pruebas junto al feature según convención vigente | Pruebas de builders, selección, clamp, IDs/handles y contadores. |
| Modificar | `frontend/package.json` y lockfile, en work unit separado | Agregar `elkjs` solo al implementar layout; no se modifica en esta auditoría. |

Reutilizable: schemas nested de `trazabilidad.schema.ts`, `GraphStatus` como semántica visual, `TIPO_PARTICIPACION`, `ESTADO_SOLICITUD`, `ESTADO_PERIODO`, `TIPO_RESPUESTA_LABELS`, formateo `es-PE`, `actionVisibility.ts`, panel de chat y mutaciones existentes. No reutilizar el layout de seis tracks ni los cinco estados paralelos de selección.

## N. Unidades de implementación delegables

| Orden | Unidad | Resultado preciso | Verificación |
|---|---|---|---|
| 1 | Normalización y labels | Modelo puro global, IDs estables, eventos ordenados globalmente y enums humanizados. | Unit tests con timestamps intercalados, nulls y enums desconocidos. |
| 2 | Rango temporal | Builder de límites/segmentos con `now` solo para abiertos y duración humana. | Tests de Solicitud cerrada, abierta, mismo día y sin eventos. |
| 3 | Timeline controlado | Headers es-PE, estilos CIP, filas/sidebar legibles, clamp y `Ajustar al trámite`. | Interacción: no salir de bounds; screenshot desktop/chat/móvil. |
| 4 | Dependencia/layout ELK | Integración aislada de `elkjs` y layout compuesto por área/ciclo. | Snapshot lógico de posiciones sin solapes y orden izquierda-derecha. |
| 5 | Nodos y aristas globales | Inicio global, ramas, participantes, estados, respuestas, terminales, merge y final; handles correctos. | Todas las edges resuelven source/target/handle; conexiones visibles. |
| 6 | Viewport legible | Zoom acotado, canvas limitado, translate extent, pan y ajuste/centrado de rama. | No bajar de piso legible con rueda, control ni fit; resize 50/50 estable. |
| 7 | Selección sincronizada | Un estado de selección; timeline centra/resalta subgrafo y nodo refleja timeline. | Tests de selección bidireccional y cambio entre ciclos sin datos stale. |
| 8 | Inspector único | Resumen compacto, progresive disclosure, identidad y acciones contextuales. | Nunca se montan dos paneles; foco vuelve al origen; acciones respetan helpers. |
| 9 | Resumen ejecutivo | Métricas activas/históricas/totales y Principal/Adjunta correctas. | Fixture finalizado muestra ceros activos junto a totales no cero. |
| 10 | Chat y responsive | Split 55/45 sin miniaturizar grafos; móvil conserva vista no modal. | 1440, 1024, 768 y 390 px; sin overflow de página. |
| 11 | Accesibilidad y regresión | Labels ARIA, teclado, contraste, alternativa textual y reduced motion. | Axe/manual keyboard, typecheck, lint, build y pruebas del feature. |

Cada unidad debe conservar código, tests y documentación relacionada en el mismo cambio revisable. No mezclar instalación/layout con la consolidación del inspector.

## O. Checklist de aceptación: `Solicitud LIMA-2026-0003`

- [ ] El resumen identifica `LIMA-2026-0003` y muestra el estado final humanizado.
- [ ] El resumen muestra `0 activas · 2 involucradas` si ambas áreas están cerradas.
- [ ] El resumen muestra ciclos cerrados/totales y participantes activos/históricos sin contradicción.
- [ ] El calendario empieza en el primer evento real y termina en el último evento/cierre real, no en hoy si está finalizada.
- [ ] `Asesoría Legal` aparece como `Principal` y `Centro Médico` como `Adjunta`.
- [ ] Los ciclos 1 de ambas áreas se alinean temporalmente y evidencian concurrencia cuando sus rangos se superponen.
- [ ] Cada barra muestra duración legible, fechas y estado; no muestra enums snake case.
- [ ] La fila global muestra segmentos de estado con duración, incluido el estado final.
- [ ] La cabecera está en español, no es roja por defecto y ningún texto aparece como `aturday, September...`.
- [ ] Pan y zoom del calendario quedan dentro del lifecycle; `Ajustar al trámite` restaura el rango.
- [ ] El flujo global parte del registro de la Solicitud antes de bifurcar áreas.
- [ ] Cada área es un grupo/swimlane con incorporación, Ciclo 1 y terminal de rama.
- [ ] Participantes aparecen con nombre completo, rol y área; alta/retiro solo cuando existen datos reales.
- [ ] La rama correspondiente contiene `Conformidad` y/o `Observación` según el payload, con emisor y fecha en inspector.
- [ ] Las ramas convergen visualmente antes del estado final de la Solicitud.
- [ ] Todas las aristas son visibles y todos sus endpoints/handles existen.
- [ ] La leyenda aclara que precedencia cronológica no equivale a causalidad.
- [ ] El zoom inicial conserva nodos legibles; no es posible alejar por debajo del piso definido.
- [ ] Si el grafo no cabe completo, se navega por pan horizontal/vertical en vez de reducirlo a miniatura.
- [ ] Clic en un ciclo del calendario resalta y centra su rama sin ocultar las demás.
- [ ] Clic en un nodo abre un único inspector compacto; no aparece una segunda tarjeta gigante.
- [ ] Las acciones solo aparecen para el ciclo operable y usuario elegible; no cambian autorización backend.
- [ ] Al abrir chat, este ocupa 45-50 % sin modal/overlay y el inspector permanece dentro del contenido principal.
- [ ] En móvil, chat es una vista no modal con retorno; los grafos conservan escala y scroll interno.
- [ ] Navegación por teclado, foco, lector de pantalla y reduced motion son verificables.

## P. No objetivos explícitos

- No cambiar backend, endpoints, presenters, modelos ni payloads.
- No agregar reglas Guardian, permisos ni autorización; los helpers siguen siendo gating de presentación.
- No inventar causalidad entre eventos cronológicamente próximos.
- No convertir React Flow en editor: sin arrastrar nodos, crear/reconectar aristas ni editar datos.
- No convertir el chat en modal, `Sheet`, overlay, diálogo o panel flotante.
- No ocultar ramas no seleccionadas; solo atenuar/resaltar y centrar.
- No reemplazar el calendario por React Flow ni usar el flujo para comunicar duración a escala.
- No instalar dependencias durante esta auditoría documental.

---

## Nota de reversión (2026-09-13)

Las implementaciones de `react-calendar-timeline` (U3) y `@xyflow/react` (U4-U6) fueron explícitamente abandonadas por decisión del usuario en favor de un único mapa de tarjetas horizontales conectadas (`SolicitudCardFlow`).

**Decisión vigente:**
- `react-calendar-timeline` fue desinstalado; `SolicitudTimelineView.tsx` y `SolicitudTimelineView.module.css` fueron eliminados.
- `@xyflow/react` y `elkjs` fueron desinstalados en una reversión anterior; los archivos asociados (`SolicitudProcessFlow.tsx`, `layoutSolicitudFlow.ts`, `SolicitudProcessFlowNodes.tsx`, `solicitud-process-flow.module.css`) fueron eliminados.
- Visualización primaria: `SolicitudCardFlow` — flujo de tarjetas CSS horizontales conectadas mediante flechas Lucide, sin librería de grafos.
- Resumen temporal: `TemporalSummary` — franja compacta que muestra inicio, fin, duración total y áreas involucradas.
- Auditoría cronológica: `ChronologicalHistory` — collapsible "Ver historial cronológico", cerrado por defecto, ordenado del más antiguo al más reciente.
- Inspector único: `TraceabilityInspector` — un solo inspector compacto debajo del flujo; sin duplicación de paneles.

**Racionales de abandono:**
- `react-calendar-timeline`: la densidad visual, el redimensionamiento no controlado y los estilos globales de la librería eran incompatibles con el sistema de diseño CIP sin hacks invasivos.
- React Flow: nodos personalizados sin `Handle` (F01), incapacidad de mostrar múltiples ciclos simultáneamente (F02), desincronización de estado entre ciclos (F03), ordenamiento por categoría en lugar de cronología (F04), y problemas de zoom/layout (F05/F06) hicieron que la librería no satisficiera los requisitos de la auditoría.

**Agentes futuros:** No reintroduzca `react-calendar-timeline`, `@xyflow/react`, `elkjs` ni ningún panel de grafos/graph-layout. La arquitectura vigente es: resumen temporal → mapa de tarjetas conectado → historial cronológico colapsable → inspector único.
