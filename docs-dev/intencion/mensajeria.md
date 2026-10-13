# Arquitectura Core de Mensajería Reutilizable

## 1. Objetivo

Construir un módulo de mensajería reutilizable y desacoplado de cualquier dominio específico.

El módulo debe servir inicialmente para `Solicitud`, pero posteriormente debe poder reutilizarse sin cambios estructurales para:

* reclamos;
* expedientes;
* incidencias;
* requerimientos;
* comunicaciones internas;
* otros módulos futuros.

La regla central es:

> El módulo de mensajería no debe saber qué es una Solicitud, un Reclamo o cualquier otra entidad de negocio.

Cada módulo se relaciona con una `Conversacion` mediante una tabla puente propia.

---

# 2. Arquitectura general

El núcleo de mensajería queda compuesto por:

```text
Conversacion
    ↓
Mensaje
    ├── MensajeAdjunto
    └── MensajeMencion
```

Los módulos externos se conectan mediante relaciones propias:

```text
Solicitud
    ↓
SolicitudConversacion
    ↓
Conversacion
```

```text
Reclamo
    ↓
ReclamoConversacion
    ↓
Conversacion
```

```text
OtroModulo
    ↓
OtroModuloConversacion
    ↓
Conversacion
```

Por lo tanto:

```text
                     MESSAGING CORE

                      Conversacion
                           │
                           ▼
                        Mensaje
                     ┌─────┴─────┐
                     │           │
                  Adjunto     Mencion


     SOLICITUDES                        RECLAMOS
          │                                │
SolicitudConversacion              ReclamoConversacion
          │                                │
          └──────────► Conversacion ◄──────┘
```

---

# 3. Principio de desacoplamiento

No se deben crear relaciones como:

```text
Mensaje.solicitud
Mensaje.reclamo
Mensaje.expediente
```

Tampoco:

```text
Conversacion.solicitud
Conversacion.reclamo
Conversacion.expediente
```

Porque eso obligaría al módulo de mensajería a conocer todos los módulos del sistema.

En su lugar:

```text
SolicitudConversacion
ReclamoConversacion
ExpedienteConversacion
...
```

pertenecen a sus respectivos módulos.

---

# 4. Tabla `Conversacion`

## Intencionalidad

Representa un hilo de comunicación.

Es únicamente el contenedor de mensajes.

No almacena información sobre permisos, áreas, solicitudes o reclamos.

## Campos

| Campo          | Tipo conceptual | Obligatorio | Descripción                       |
| -------------- | --------------- | ----------: | --------------------------------- |
| `id`           | UUID            |          Sí | PK heredada de `BaseModel`.       |
| `titulo`       | String          |          No | Título opcional del hilo.         |
| `creada_por`   | FK Usuario      |          Sí | Usuario que creó la conversación. |
| `fecha_inicio` | DateTime        |          Sí | Fecha funcional de inicio.        |
| `cerrada_at`   | DateTime        |          No | Fecha funcional de cierre.        |
| `cerrada_por`  | FK Usuario      |          No | Actor que cerró la conversación.  |
| `created_at`   | DateTime        |  Automático | Inserción técnica.                |
| `updated_at`   | DateTime        |  Automático | Modificación técnica.             |

## Regla de estado

No es necesario agregar inicialmente:

```text
activo
estado = ABIERTA/CERRADA
```

si puede derivarse de:

```text
cerrada_at IS NULL
```

Interpretación:

```text
cerrada_at IS NULL
→ conversación abierta
```

```text
cerrada_at IS NOT NULL
→ conversación cerrada
```

---

# 5. Tabla `Mensaje`

## Intencionalidad

Representa cada mensaje individual dentro de una conversación.

## Campos

| Campo           | Tipo conceptual | Obligatorio | Descripción                                      |
| --------------- | --------------- | ----------: | ------------------------------------------------ |
| `id`            | UUID            |          Sí | PK.                                              |
| `conversacion`  | FK Conversacion |          Sí | Conversación propietaria.                        |
| `autor_usuario` | FK Usuario      |          Sí | Usuario que envió el mensaje.                    |
| `contenido`     | Text            |          No | Texto del mensaje.                               |
| `fecha_envio`   | DateTime        |          Sí | Fecha funcional real de envío.                   |
| `mensaje_padre` | FK self         |          No | Mensaje al que responde, si se soportan replies. |
| `editado_at`    | DateTime        |          No | Fecha de edición.                                |
| `eliminado_at`  | DateTime        |          No | Baja lógica.                                     |
| `eliminado_por` | FK Usuario      |          No | Actor que eliminó funcionalmente el mensaje.     |
| `created_at`    | DateTime        |  Automático | Inserción técnica.                               |
| `updated_at`    | DateTime        |  Automático | Modificación técnica.                            |

## Importante

No agregar:

```text
area
solicitud
reclamo
periodo
```

al mensaje.

El usuario ya identifica quién escribió.

El contexto institucional se obtiene a través del módulo propietario de la conversación.

---

# 6. Regla de contenido del mensaje

Un mensaje debe contener al menos uno de los siguientes elementos:

```text
contenido
```

o:

```text
uno o más adjuntos
```

o ambos.

No permitir:

```text
contenido = NULL
sin adjuntos
```

---

# 7. Tabla `MensajeAdjunto`

## Intencionalidad

Representa archivos enviados dentro de un mensaje.

El adjunto pertenece al `Mensaje`, no directamente a `Conversacion`.

## Campos

| Campo             | Tipo conceptual | Obligatorio | Descripción                       |
| ----------------- | --------------- | ----------: | --------------------------------- |
| `id`              | UUID            |          Sí | PK.                               |
| `mensaje`         | FK Mensaje      |          Sí | Mensaje propietario.              |
| `archivo`         | FileField       |          Sí | Archivo almacenado.               |
| `nombre_original` | String          |          Sí | Nombre original del archivo.      |
| `mime_type`       | String          |          No | Tipo MIME validado.               |
| `tamano_bytes`    | BigInteger      |          No | Tamaño del archivo.               |
| `subido_por`      | FK Usuario      |          Sí | Usuario que adjuntó el archivo.   |
| `fecha_archivo`   | DateTime        |          Sí | Fecha funcional de incorporación. |
| `created_at`      | DateTime        |  Automático | Inserción técnica.                |
| `updated_at`      | DateTime        |  Automático | Modificación técnica.             |

Ejemplo:

```text
Mensaje
"Adjunto los documentos solicitados."

    ├── plano.pdf
    ├── informe.docx
    └── captura.png
```

---

# 8. Tabla `MensajeMencion`

## Intencionalidad

Registrar menciones explícitas a usuarios dentro de un mensaje.

Ejemplo:

```text
"@Juan revisa este documento."
```

## Campos

| Campo        | Tipo conceptual | Obligatorio | Descripción                      |
| ------------ | --------------- | ----------: | -------------------------------- |
| `id`         | UUID            |          Sí | PK.                              |
| `mensaje`    | FK Mensaje      |          Sí | Mensaje que contiene la mención. |
| `usuario`    | FK Usuario      |          Sí | Usuario mencionado.              |
| `created_at` | DateTime        |  Automático | Registro técnico.                |

## Constraint

```text
UNIQUE(mensaje, usuario)
```

No crear múltiples filas idénticas para la misma mención funcional.

---

# 9. Integración con notificaciones

Una mención puede disparar el core de notificaciones.

Ejemplo:

```text
Pedro escribe:

"@Juan revisa este documento."
        ↓
Mensaje
        ↓
MensajeMencion
        ↓
evento CHAT_MENCION
        ↓
Notificacion
        ↓
NotificacionUsuario(Juan)
```

El módulo de mensajería no debe crear otro sistema de notificaciones.

Debe reutilizar el módulo transversal de notificaciones existente.

---

# 10. Tabla `SolicitudConversacion`

## Ubicación

Esta tabla pertenece al módulo de solicitudes/trámites, no al Messaging Core.

## Intencionalidad

Relacionar una `Solicitud` con una `Conversacion`.

## Campos

| Campo          | Tipo conceptual | Obligatorio | Descripción                         |
| -------------- | --------------- | ----------: | ----------------------------------- |
| `id`           | UUID            |          Sí | PK.                                 |
| `solicitud`    | FK Solicitud    |          Sí | Solicitud propietaria del contexto. |
| `conversacion` | FK Conversacion |          Sí | Conversación relacionada.           |
| `created_at`   | DateTime        |  Automático | Registro técnico.                   |
| `updated_at`   | DateTime        |  Automático | Modificación técnica.               |

## Primera versión

Inicialmente se recomienda:

```text
UNIQUE(solicitud)
UNIQUE(conversacion)
```

De modo que:

```text
1 Solicitud
    ↓
1 Conversacion general
```

---

# 11. Quién puede conversar en una Solicitud

El Messaging Core no debe decidir permisos.

El módulo de Solicitudes ya contiene la información necesaria:

```text
Solicitud
   ↓
SolicitudAsignacion
   ↓
SolicitudAsignacionPeriodo
   ↓
Áreas participantes
   ↓
Usuarios habilitados
```

Por lo tanto, cuando un usuario quiera ingresar o escribir en la conversación:

```text
Usuario
   ↓
SolicitudConversacion
   ↓
Solicitud
   ↓
reglas del módulo Solicitudes
   ↓
¿puede ver/escribir?
```

El acceso puede depender de:

* áreas actualmente involucradas;
* períodos activos;
* usuarios vinculados;
* reglas futuras de permisos.

No se debe duplicar esa información dentro del módulo de mensajería.

---

# 12. No crear `ConversacionArea`

No se recomienda actualmente crear:

```text
ConversacionArea
```

porque la Solicitud ya sabe qué áreas participan.

Crear esa tabla duplicaría la misma información.

Ejemplo incorrecto:

```text
SolicitudAsignacionPeriodo
→ Arquitectura activa
```

y adicionalmente:

```text
ConversacionArea
→ Arquitectura activa
```

Existirían dos fuentes de verdad.

Esto debe evitarse.

---

# 13. No crear `ConversacionParticipanteUsuario`

Tampoco se recomienda actualmente:

```text
ConversacionParticipanteUsuario
```

si los permisos pueden resolverse utilizando las entidades existentes del módulo propietario.

Para una Solicitud, el módulo ya conoce:

```text
qué usuarios intervienen
qué áreas están involucradas
qué períodos están vigentes
```

La conversación debe reutilizar esa información.

---

# 14. Regla general de permisos

La responsabilidad se divide así:

```text
Messaging Core
==============
guardar conversación
guardar mensajes
guardar adjuntos
guardar menciones
```

Mientras:

```text
Módulo consumidor
==================
decidir quién puede:
- ver
- escribir
- responder
- adjuntar
```

---

# 15. Arquitectura de permisos por dominio

Conceptualmente puede existir:

```text
SolicitudConversationPolicy
```

con operaciones como:

```text
can_view(usuario, solicitud)
can_write(usuario, solicitud)
```

Posteriormente:

```text
ReclamoConversationPolicy
```

puede tener reglas completamente diferentes:

```text
can_view(usuario, reclamo)
can_write(usuario, reclamo)
```

El `MessagingService` sigue siendo el mismo.

---

# 16. Reutilización para Reclamos

Cuando exista un módulo de reclamos, solo se agrega:

```text
ReclamoConversacion
-------------------
id
reclamo FK
conversacion FK
created_at
updated_at
```

La arquitectura pasa a ser:

```text
Reclamo
    ↓
ReclamoConversacion
    ↓
Conversacion
    ↓
Mensaje
    ├── MensajeAdjunto
    └── MensajeMencion
```

Las reglas de permiso pertenecen al módulo Reclamos.

Ejemplo:

```text
ReclamoConversationPolicy
```

El Messaging Core no cambia.

---

# 17. Reutilización para otros módulos

El mismo patrón puede replicarse:

```text
ExpedienteConversacion
IncidenciaConversacion
RequerimientoConversacion
ProyectoConversacion
```

Cada uno contiene:

```text
objeto_del_dominio FK
conversacion FK
```

y el dominio define sus propias reglas de acceso.

---

# 18. Ejemplo de arquitectura completa

```text
                          MESSAGING CORE

                           Conversacion
                                │
                                ▼
                             Mensaje
                         ┌──────┴──────┐
                         │             │
                    MensajeAdjunto  MensajeMencion
                                         │
                                         ▼
                                 Notifications Core


       SOLICITUDES                               RECLAMOS

       Solicitud                                  Reclamo
           │                                         │
           ▼                                         ▼
SolicitudConversacion                      ReclamoConversacion
           │                                         │
           └──────────────► Conversacion ◄───────────┘
```

---

# 19. Servicio de mensajería

El módulo debe exponer servicios genéricos.

Ejemplo conceptual:

```text
MessagingService
----------------
crear_conversacion(...)
crear_mensaje(...)
editar_mensaje(...)
eliminar_mensaje(...)
obtener_mensajes(...)
```

El servicio recibe una conversación ya autorizada.

No debe hacer internamente:

```text
if solicitud:
    ...
elif reclamo:
    ...
elif expediente:
    ...
```

Eso rompería el desacoplamiento.

---

# 20. Flujo para crear un mensaje desde Solicitud

Ejemplo:

```text
POST /solicitudes/{id}/mensajes
```

Flujo:

```text
Controller
    ↓
SolicitudMessagingFlow
    ↓
resolver Solicitud
    ↓
validar permiso del usuario
    ↓
obtener SolicitudConversacion
    ↓
MessagingService.crear_mensaje(...)
```

El `MessagingService` solo recibe:

```text
conversacion
usuario
contenido
adjuntos
menciones
```

No necesita recibir la Solicitud.

---

# 21. Flujo para crear un mensaje desde Reclamo

Posteriormente:

```text
POST /reclamos/{id}/mensajes
```

Flujo:

```text
Controller
    ↓
ReclamoMessagingFlow
    ↓
resolver Reclamo
    ↓
validar permiso
    ↓
obtener ReclamoConversacion
    ↓
MessagingService.crear_mensaje(...)
```

Exactamente el mismo núcleo de mensajería.

---

# 22. Transacción de creación de mensaje

Crear un mensaje puede implicar:

```text
Mensaje
+
MensajeAdjunto[]
+
MensajeMencion[]
+
eventos de notificación
```

Debe tratarse como una operación funcional única.

Conceptualmente:

```text
transaction.atomic()

    crear Mensaje

    crear adjuntos

    crear menciones

    registrar/generar eventos necesarios
```

La transacción debe vivir en la capa de flujo/use case que coordina la operación.

---

# 23. Eliminación

Por tratarse de un sistema con trazabilidad institucional, evitar eliminación física como flujo normal.

Utilizar:

```text
Mensaje.eliminado_at
Mensaje.eliminado_por
```

Así se conserva evidencia histórica.

---

# 24. Edición

Inicialmente puede registrarse:

```text
editado_at
```

Si en el futuro se requiere conservar cada versión del contenido, se puede agregar:

```text
MensajeVersion
```

No es necesario implementarlo en esta primera etapa.

---

# 25. Respuestas a mensajes

Si se desea soportar:

```text
Responder a mensaje
```

puede utilizarse:

```text
Mensaje.mensaje_padre
```

como FK nullable hacia el mismo modelo.

Ejemplo:

```text
Mensaje #10
"¿Ya se revisó el expediente?"

    ↓ respuesta

Mensaje #15
mensaje_padre = #10
"Sí, se revisó esta mañana."
```

No crear otra tabla únicamente para respuestas.

---

# 26. Tablas a implementar ahora

## Messaging Core

```text
Conversacion
Mensaje
MensajeAdjunto
MensajeMencion
```

`MensajeMencion` puede omitirse inicialmente si todavía no se implementarán menciones.

---

## Integración con Solicitudes

```text
SolicitudConversacion
```

---

# 27. Tablas que NO deben implementarse ahora

No crear por el momento:

```text
ConversacionArea
ConversacionParticipanteUsuario
MensajeLectura
ConversacionLecturaUsuario
ReclamoConversacion
ExpedienteConversacion
MensajeVersion
```

salvo que exista ya una necesidad funcional concreta.

---

# 28. Campos finales resumidos

## `Conversacion`

```text
id
titulo nullable
creada_por
fecha_inicio
cerrada_at nullable
cerrada_por nullable
created_at
updated_at
```

---

## `Mensaje`

```text
id
conversacion
autor_usuario
contenido nullable
fecha_envio
mensaje_padre nullable
editado_at nullable
eliminado_at nullable
eliminado_por nullable
created_at
updated_at
```

---

## `MensajeAdjunto`

```text
id
mensaje
archivo
nombre_original
mime_type nullable
tamano_bytes nullable
subido_por
fecha_archivo
created_at
updated_at
```

---

## `MensajeMencion`

```text
id
mensaje
usuario
created_at
updated_at
```

Constraint:

```text
UNIQUE(mensaje, usuario)
```

---

## `SolicitudConversacion`

```text
id
solicitud
conversacion
created_at
updated_at
```

Inicialmente:

```text
UNIQUE(solicitud)
UNIQUE(conversacion)
```

---

# 29. Regla arquitectónica principal

El sistema debe conservar esta separación:

```text
DOMINIO
decide:
- quién tiene acceso
- quién puede escribir
- quién puede ver
```

```text
MESSAGING CORE
decide:
- cómo guardar conversación
- cómo guardar mensaje
- cómo guardar adjunto
- cómo guardar mención
```

No mezclar ambas responsabilidades.

---

# 30. Resultado esperado

La primera implementación queda:

```text
Solicitud
    ↓
SolicitudConversacion
    ↓
Conversacion
    ↓
Mensaje
    ├── MensajeAdjunto
    └── MensajeMencion
```

Posteriormente:

```text
Reclamo
    ↓
ReclamoConversacion
    ↓
Conversacion
```

sin modificar:

```text
Conversacion
Mensaje
MensajeAdjunto
MensajeMencion
```

La misma arquitectura puede repetirse para cualquier otro módulo.

---

# 31. Intencionalidad final

No se busca crear específicamente:

```text
ChatSolicitud
```

Se busca construir un:

```text
Messaging Core
```

reutilizable.

Cada módulo solamente debe aportar:

```text
1. una tabla puente hacia Conversacion;
2. sus reglas de permisos;
3. sus endpoints/use cases específicos.
```

Por lo tanto:

```text
Solicitud
→ SolicitudConversacion
```

```text
Reclamo
→ ReclamoConversacion
```

```text
OtroModulo
→ OtroModuloConversacion
```

pero todos consumen:

```text
Conversacion
Mensaje
MensajeAdjunto
MensajeMencion
```

Esta debe ser la base arquitectónica de la implementación.
