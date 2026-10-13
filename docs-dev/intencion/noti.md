# Informe de arquitectura e intencionalidad

## Evolución del módulo de notificaciones

### 1. Objetivo

El módulo de notificaciones debe entenderse como una capacidad transversal del sistema y no únicamente como una funcionalidad asociada al flujo actual de solicitudes.

La implementación existente resuelve correctamente la necesidad inmediata: comunicar eventos generados durante la gestión de una solicitud hacia un área y registrar posteriormente la interacción individual de los usuarios pertenecientes a dicha área.

Sin embargo, el crecimiento previsto del sistema introduce nuevos escenarios:

* notificaciones directas a usuarios;
* comunicaciones hacia áreas;
* menciones dentro de conversaciones;
* mensajes relacionados con reclamos;
* requerimientos entre áreas o usuarios;
* eventos producidos por respuestas;
* comunicaciones asociadas a nuevos módulos;
* eventualmente, entrega mediante otros canales.

Por este motivo, la arquitectura debe conservar la solución actual, pero evitar que `Notificacion` quede acoplada exclusivamente al módulo de solicitudes.

---

# 2. Situación actual

Actualmente el modelo puede resumirse así:

```text
Solicitud / flujo operativo
        │
        ▼
   Notificacion
        │
        │ evento dirigido al área
        ▼
NotificacionUsuario
        │
        ├── vista_at
        ├── abierta_at
        └── descartada_at
```

La responsabilidad actual está correctamente separada.

### `Notificacion`

Representa el evento institucional que debe ser comunicado.

Por ejemplo:

```text
Nueva asignación de una solicitud
Cambio de participación
Reincorporación de un área
Corrección de asignación
```

### `NotificacionUsuario`

Representa la relación individual entre ese evento y cada persona que podía consumirlo.

Permite registrar independientemente:

```text
vista_at
abierta_at
descartada_at
```

Esto evita cometer el error de considerar una notificación institucional como «leída» simplemente porque uno de los integrantes del área la abrió.

---

# 3. Servicios actuales

La lógica actual se encuentra distribuida principalmente en:

```text
SolicitudFlujo
    └── crea Notificacion
    └── crea NotificacionUsuario
```

y:

```text
NotificacionFlujo
    ├── marcar vista
    ├── abrir
    └── descartar
```

con:

```text
NotificacionOrchestrator
    └── fachada utilizada por los controllers
```

Esta estructura es válida para el estado actual.

La principal mejora conceptual consiste en que **la generación de notificaciones no debería seguir perteneciendo a `SolicitudFlujo`**.

`SolicitudFlujo` debe saber que ocurrió un evento de negocio.

El módulo de notificaciones debe saber cómo convertir ese evento en una notificación y cómo resolver sus destinatarios.

Por ello tiene sentido extraer gradualmente la creación hacia un servicio propio:

```text
NotificacionService
```

De esa forma:

```text
Solicitud
Chat
Reclamos
Respuestas
otros módulos
```

podrán utilizar la misma capacidad sin duplicar lógica.

---

# 4. La arquitectura actual no debe descartarse

La arquitectura existente no representa un error.

Representa una implementación especializada de una arquitectura más amplia.

Actualmente:

```text
Notificacion
→ siempre se origina en solicitudes
→ prácticamente siempre tiene como audiencia un área
```

En el futuro:

```text
Notificacion
→ puede originarse en cualquier módulo
→ puede estar dirigida a diferentes tipos de destinatario
```

Por lo tanto, la evolución natural es:

```text
HOY

Solicitud
   ↓
Notificacion
   ↓
Área
   ↓
NotificacionUsuario
```

hacia:

```text
FUTURO

Cualquier módulo
      ↓
Notificacion
      ↓
Audiencia
      ↓
Destinatarios individuales
```

No es necesario reconstruir lo existente.

La intención debe ser **extraer progresivamente las responsabilidades que actualmente están implícitas**.

---

# 5. Separación fundamental: evento, contexto y destinatario

Para mantener el módulo realmente extensible deben existir conceptualmente tres dimensiones independientes.

## 5.1 Evento

Responde a:

> ¿Qué ocurrió?

Ejemplos:

```text
NUEVA_ASIGNACION
CAMBIO_PARTICIPACION
CASO_TOMADO
RECLAMO_CREADO
RECLAMO_RESPONDIDO
CHAT_MENCION
CHAT_MENSAJE
RESPUESTA_EMITIDA
REQUERIMIENTO_CREADO
```

Esto corresponde al concepto:

```text
tipo_evento
```

Conviene utilizar un único nombre en todo el sistema.

La recomendación es:

```text
tipo_evento
```

en lugar de alternar entre:

```text
tipo
tipo_notificacion
tipo_evento
```

---

# 6. La audiencia es una dimensión diferente

La audiencia responde a:

> ¿A quién debe comunicarse este evento?

Aquí aparece una corrección importante respecto a la propuesta:

```text
AREA
USUARIO
MENCION
```

`MENCION` no debería ser una audiencia.

Una mención describe **lo que ocurrió**, no quién recibe.

Por ejemplo:

```text
tipo_evento = CHAT_MENCION
audiencia = USUARIO
```

El usuario mencionado es el destinatario.

Otro ejemplo:

```text
tipo_evento = NUEVA_ASIGNACION
audiencia = AREA
```

Por tanto, inicialmente las audiencias reales pueden ser simplemente:

```text
AREA
USUARIO
```

Y si en algún momento aparece una necesidad real:

```text
GRUPO
USUARIO_EXTERNO
ROL
```

podrá extenderse sin modificar la semántica de los eventos.

---

# 7. Contexto de la notificación

Existe una tercera pregunta independiente:

> ¿Sobre qué elemento del sistema ocurrió?

Ejemplo:

```text
NUEVA_ASIGNACION
→ Solicitud 100
```

```text
CHAT_MENCION
→ Conversación 20 / Mensaje 455
```

```text
RECLAMO_RESPONDIDO
→ Reclamo 350
```

```text
RESPUESTA_EMITIDA
→ Respuesta 71
```

Esto no debe confundirse ni con el evento ni con el destinatario.

Por tanto:

```text
EVENTO
¿qué ocurrió?

CONTEXTO
¿sobre qué ocurrió?

AUDIENCIA
¿a quién se comunica?
```

Esta separación constituye la principal base arquitectónica para que el módulo pueda crecer.

---

# 8. Núcleo conceptual futuro

La estructura conceptual puede representarse de la siguiente manera:

```text
                     Notificacion
                          │
             ┌────────────┼─────────────┐
             │            │             │
          EVENTO       CONTEXTO      AUDIENCIA
             │            │             │
             │            │       ┌─────┴─────┐
             │            │       │           │
             │            │     Área       Usuario
             │            │
             │      ┌─────┼────────────┐
             │      │     │            │
             │ Solicitud  Chat      Reclamo
             │
             ▼
       tipo_evento
```

Posteriormente:

```text
Audiencia
    ↓
materialización
    ↓
NotificacionUsuario
    ↓
vista / apertura / descarte
```

---

# 9. `NotificacionUsuario` debe mantenerse

`NotificacionUsuario` es una pieza importante y no debería eliminarse.

Incluso si la notificación se dirige originalmente a un área, es necesario conservar quiénes eran los usuarios destinatarios en ese momento.

Ejemplo:

```text
Notificación #500
Área: Arquitectura
```

Usuarios vigentes al generarse:

```text
Juan
Pedro
María
```

Se materializa:

```text
NotificacionUsuario
#500 → Juan

NotificacionUsuario
#500 → Pedro

NotificacionUsuario
#500 → María
```

De esta manera se conserva históricamente quién podía conocer ese evento.

Si posteriormente ingresa un nuevo trabajador al área, no debería aparecer retroactivamente como destinatario de una notificación creada antes de su incorporación.

Esta característica es especialmente importante para la trazabilidad y para las métricas.

---

# 10. Audiencia institucional e interacción personal

Debe mantenerse la separación:

```text
NotificacionArea
```

representa:

> El evento estaba destinado institucionalmente al Área X.

Mientras:

```text
NotificacionUsuario
```

representa:

> Este usuario concreto podía consumirlo y así interactuó con él.

Por ejemplo:

```text
Notificacion
       │
       ├── NotificacionArea
       │      └── Arquitectura
       │
       └── NotificacionUsuario
              ├── Juan
              ├── Pedro
              └── María
```

Esto ofrece dos niveles de información:

```text
responsabilidad institucional
+
interacción individual
```

Algo particularmente útil para el sistema actual.

---

# 11. Notificaciones directas a usuarios

El mismo núcleo debe permitir:

```text
Notificacion
       │
       └── NotificacionUsuario
              └── Juan
```

sin necesidad de crear una `NotificacionArea`.

Este caso aparecerá naturalmente con funcionalidades como:

```text
menciones
mensajes directos
requerimientos personales
recordatorios
acciones asignadas
```

Por tanto, una notificación no debe requerir obligatoriamente un área.

---

# 12. Extensión por módulos

No es conveniente llenar `Notificacion` con referencias opcionales a todos los futuros módulos:

```text
solicitud_id
chat_id
mensaje_id
reclamo_id
respuesta_id
requerimiento_id
...
```

porque con el tiempo produciría una tabla altamente acoplada y llena de campos `NULL`.

Una arquitectura más modular permite que los propios módulos agreguen su contexto.

Conceptualmente:

```text
notifications
    Notificacion
    NotificacionUsuario
    NotificacionArea
```

Mientras:

```text
tramites
    NotificacionSolicitud
```

```text
chat
    NotificacionChat
```

```text
reclamos
    NotificacionReclamo
```

```text
respuestas
    NotificacionRespuesta
```

De esta forma el núcleo de notificaciones no necesita conocer todos los módulos futuros.

Son los módulos los que utilizan el núcleo.

La dirección de dependencia queda:

```text
Solicitudes ──┐
Chat ─────────┤
Reclamos ─────┼──► Notifications Core
Respuestas ───┤
Otros ────────┘
```

y no:

```text
Notifications
      ↓
conoce internamente todos los módulos
```

---

# 13. Ejemplo: solicitud

Cuando una solicitud incorpora Arquitectura:

```text
Evento:
NUEVA_ASIGNACION
```

se genera:

```text
Notificacion
tipo_evento = NUEVA_ASIGNACION
```

contexto:

```text
NotificacionSolicitud
solicitud = X
periodo = Y
```

audiencia:

```text
NotificacionArea
area = Arquitectura
```

materialización:

```text
NotificacionUsuario
→ usuarios activos de Arquitectura
```

---

# 14. Ejemplo: mención dentro de un chat

Supongamos:

```text
Pedro:
"@Juan revisa este documento."
```

El chat genera:

```text
tipo_evento = CHAT_MENCION
```

contexto:

```text
NotificacionChat
conversacion = X
mensaje = Y
```

destinatario:

```text
NotificacionUsuario
usuario = Juan
```

No existe necesidad de:

```text
NotificacionArea
```

porque la audiencia no es institucional.

---

# 15. Ejemplo: mensaje dirigido a un área

También puede existir:

```text
Área Arquitectura
→ envía mensaje a Área Legal
```

El evento podría ser:

```text
CHAT_MENSAJE_AREA
```

contexto:

```text
NotificacionChat
```

audiencia:

```text
NotificacionArea
→ Legal
```

y posteriormente:

```text
NotificacionUsuario
→ integrantes elegibles de Legal
```

Nuevamente se utiliza el mismo núcleo.

---

# 16. Reclamos

La misma arquitectura permite que el futuro módulo de reclamos produzca:

```text
RECLAMO_CREADO
RECLAMO_OBSERVADO
RECLAMO_ESCALADO
RECLAMO_RESPONDIDO
RECLAMO_VENCIDO
```

sin modificar el modelo principal de notificaciones.

El módulo solamente registra su relación:

```text
NotificacionReclamo
```

y utiliza los mecanismos existentes para determinar la audiencia.

---

# 17. Respuestas al usuario

Un escenario importante de expansión será el cierre del circuito hacia el usuario o administrado.

Ejemplo:

```text
SolicitudAsignacionRespuesta
        ↓
respuesta emitida
        ↓
RESPUESTA_EMITIDA
        ↓
Notificacion
```

Actualmente podría utilizarse únicamente para comunicación interna.

Más adelante el mismo evento podría originar:

```text
notificación en portal
correo
push
otro canal institucional
```

sin modificar la lógica propia de las respuestas.

Esta separación es importante:

```text
Respuesta
= hecho de negocio

Notificacion
= comunicación sobre ese hecho
```

---

# 18. Notificación no debe convertirse en tarea

Otro principio importante para preservar la arquitectura:

Una notificación puede comunicar que existe una tarea, pero **no debe convertirse ella misma en la tarea**.

Por ejemplo:

```text
Requerimiento
-------------
estado
fecha_limite
responsable
contenido
```

es una entidad de negocio.

Su creación puede producir:

```text
Notificacion
tipo_evento = REQUERIMIENTO_CREADO
```

Pero no deberían almacenarse dentro de `Notificacion`:

```text
estado del requerimiento
fecha límite del requerimiento
resolución
aceptación
```

La notificación comunica.

El módulo propietario mantiene la verdad del negocio.

---

# 19. Contrato con frontend

El frontend tampoco debería deducir comportamiento basándose únicamente en textos.

Debe recibir información estructurada.

Ejemplo conceptual:

```text
tipo_evento
categoria
severidad
contexto
estado_individual
acción disponible
```

Entonces puede mapear:

```text
NUEVA_ASIGNACION
→ icono de solicitud
→ abrir revisión de solicitud
```

```text
CHAT_MENCION
→ icono de conversación
→ abrir mensaje
```

```text
RECLAMO_RESPONDIDO
→ icono de reclamo
→ abrir reclamo
```

Sin hardcodear títulos o analizar textos.

---

# 20. `tipo_evento` como contrato estable

Es especialmente importante que los códigos sean semánticos y estables.

Por ejemplo:

```text
SOLICITUD_NUEVA_ASIGNACION
SOLICITUD_REINCORPORACION
SOLICITUD_CAMBIO_PARTICIPACION

CHAT_MENCION
CHAT_MENSAJE_AREA

RECLAMO_NUEVO
RECLAMO_RESPONDIDO

RESPUESTA_EMITIDA
```

Esto facilita:

* frontend;
* métricas;
* filtros;
* debugging;
* auditoría;
* pruebas;
* integraciones futuras.

Los códigos deben representar eventos de negocio, no componentes visuales.

No:

```text
ICONO_ROJO
ALERTA_AMARILLA
CARD_CHAT
```

---

# 21. Estado individual

El estado de lectura debe continuar siendo individual.

Puede derivarse de:

```text
vista_at
abierta_at
descartada_at
```

No es necesario duplicarlo inicialmente con otro campo persistido.

El backend sí puede exponer un valor calculado:

```text
NO_VISTA
VISTA
ABIERTA
DESCARTADA
```

para simplificar el frontend.

Esto también habilita el filtro actualmente pendiente:

```text
?estado_individual=NO_VISTA
```

sin introducir otra fuente de verdad.

---

# 22. Resumen de notificaciones

El futuro:

```text
GET /notificaciones/resumen
```

tiene sentido como endpoint agregado para UI.

Puede responder información como:

```text
total_no_vistas
total_abiertas
total_por_categoria
hay_urgentes
```

pero estos valores deben calcularse utilizando los registros individuales del usuario.

No debe introducir un segundo sistema de estados.

---

# 23. Enriquecimiento de presenters

Campos como:

```text
solicitud_asunto
periodo_ciclo
periodo_activo
participo
```

son útiles para frontend.

Sin embargo, conceptualmente son datos de presentación.

No deben convertirse en columnas duplicadas dentro de `Notificacion`.

La fuente continúa siendo:

```text
Solicitud
Periodo
SolicitudAsignacionUsuario
```

y el presenter/selectors construye la respuesta enriquecida.

Esto mantiene la normalización y evita inconsistencias.

---

# 24. Responsabilidad de `NotificacionService`

La extracción hacia un servicio propio tiene una intención arquitectónica importante.

Este servicio puede convertirse en la única entrada para generación de notificaciones.

Conceptualmente:

```text
crear_evento(...)
notificar_area(...)
notificar_usuario(...)
materializar_destinatarios(...)
```

Los módulos consumidores no necesitan conocer la implementación interna.

Por ejemplo:

```text
SolicitudFlujo
    ↓
"ocurrió NUEVA_ASIGNACION"
    ↓
NotificacionService
```

o:

```text
Chat
    ↓
"ocurrió CHAT_MENCION"
    ↓
NotificacionService
```

Esto elimina duplicaciones conforme aparecen nuevos módulos.

---

# 25. Separación entre generación e interacción

Debe mantenerse además la separación entre:

```text
GENERACIÓN
```

y:

```text
CONSUMO
```

Generación:

```text
NotificacionService
```

Consumo:

```text
NotificacionFlujo
    ├── vista
    ├── abrir
    └── descartar
```

Son problemas diferentes.

El primero responde:

> ¿Quién debe recibir este evento?

El segundo:

> ¿Qué hizo un usuario con una notificación ya existente?

Mantenerlos separados permitirá escalar ambos lados independientemente.

---

# 26. Futuro: canales de entrega

La arquitectura descrita tampoco obliga a que una notificación sea únicamente «in-app».

Más adelante podría existir:

```text
NotificacionEntrega
```

capaz de registrar:

```text
canal
estado
fecha_envio
intentos
error
```

y soportar:

```text
IN_APP
EMAIL
PUSH
WEBSOCKET
otros canales
```

Sin embargo, esta capacidad no es necesaria actualmente.

Lo importante es que el modelo actual no impida añadirla.

---

# 27. Lo que no conviene implementar todavía

La intención futura no implica construir anticipadamente:

* sistema completo de plantillas;
* email;
* push;
* colas;
* preferencias por usuario;
* reintentos;
* WebSocket;
* múltiples canales;
* reglas complejas de suscripción;
* event bus distribuido.

Sería sobreingeniería en el estado actual.

La arquitectura debe simplemente garantizar que estas capacidades puedan agregarse sin rehacer el núcleo.

---

# 28. Semilla recomendada

La semilla conceptual puede mantenerse pequeña:

```text
Notificacion
    │
    ├── tipo_evento
    ├── título
    ├── mensaje
    ├── actor
    └── fecha_evento

NotificacionArea
    │
    ├── notificacion
    └── area

NotificacionUsuario
    │
    ├── notificacion
    ├── usuario
    ├── vista_at
    ├── abierta_at
    └── descartada_at
```

Más las relaciones específicas que cada módulo requiera:

```text
NotificacionSolicitud
NotificacionChat
NotificacionReclamo
...
```

No todas deben existir hoy.

Se crean cuando el módulo correspondiente exista.

---

# 29. Relación con lo implementado actualmente

La arquitectura existente puede mapearse directamente:

```text
ACTUAL
Notificacion.area
```

evoluciona conceptualmente a:

```text
NotificacionArea
```

Mientras:

```text
NotificacionUsuario
```

se conserva prácticamente igual.

La lógica hoy contenida en:

```text
SolicitudFlujo
```

para crear notificaciones se extrae progresivamente hacia:

```text
NotificacionService
```

Y:

```text
NotificacionFlujo
```

continúa administrando la interacción individual.

Por tanto, **el trabajo actual no se pierde**.

Es una especialización inicial del núcleo futuro.

---

# 30. Intencionalidad arquitectónica final

La meta no es construir «un sistema de notificaciones muy complejo».

La meta es que `Notificacion` deje de significar:

> «Aviso generado por una Solicitud para un Área».

y pase a significar:

> «Representación persistente de un evento del sistema que debe ser comunicado a uno o más destinatarios».

Después, cada módulo define su contexto.

Cada audiencia define sus receptores.

Y cada usuario mantiene su propia interacción.

La arquitectura puede resumirse como:

```text
                   EVENTO DE NEGOCIO
                          │
                          ▼
                    NOTIFICACION
                          │
             ┌────────────┴────────────┐
             │                         │
          CONTEXTO                  AUDIENCIA
             │                         │
     ┌───────┼────────┐         ┌──────┴──────┐
     │       │        │         │             │
Solicitud   Chat   Reclamo     Área        Usuario
                                     
                          │
                          ▼
                NotificacionUsuario
                          │
                  ┌───────┼─────────┐
                  │       │         │
                vista   abierta   descartada
```

Este diseño conserva la simplicidad necesaria para la etapa actual, pero evita acoplar una capacidad transversal a un único módulo.

---

# 31. Conclusión

El módulo existente se encuentra correctamente encaminado.

No existe una necesidad de reemplazarlo.

Lo que se requiere es **hacer explícita la abstracción que ya está empezando a aparecer**.

Actualmente:

```text
Notificacion
+
NotificacionUsuario
```

ya proporcionan la base correcta.

Las principales decisiones que permitirán que esa base crezca de forma saludable son:

1. centralizar progresivamente la generación en un `NotificacionService`;
2. utilizar un concepto único de `tipo_evento`;
3. separar evento, contexto y audiencia;
4. considerar `AREA` y `USUARIO` como audiencias reales;
5. considerar `MENCION` como un evento, no como audiencia;
6. no obligar a que toda notificación pertenezca a una Solicitud;
7. no obligar a que toda notificación pertenezca a un Área;
8. conservar `NotificacionUsuario` como evidencia individual;
9. permitir que cada módulo agregue su propio contexto;
10. evitar implementar hoy capacidades futuras que todavía no son necesarias.

El resultado es una arquitectura pequeña en su primera versión, pero con una dirección clara:

```text
hoy:
solicitudes

mañana:
solicitudes + reclamos

después:
solicitudes + reclamos + chat + requerimientos + respuestas

sin reemplazar el núcleo de notificaciones.
```

Ese es el principal valor del diseño: **la expansión futura ocurre agregando capacidades alrededor del núcleo, no reconstruyendo el núcleo cada vez que aparece un nuevo módulo.**
