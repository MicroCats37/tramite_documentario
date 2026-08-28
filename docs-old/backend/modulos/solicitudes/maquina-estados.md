# Máquina de Estados — Solicitudes

## Overview

El módulo solicitudes implementa una **máquina de estados finitos (FSM)** con 4 estados activos y 1 estado absorbente (`CERRADO`). La mutación de estado está gobernada por reglas de transición explícitas validadas en tres capas:

1. **Capa de permisos** (`permissions/rol/*`): ¿El usuario tiene derecho a editar este estado?
2. **Capa del serializer** (`validate()` en `SolicitudMutationSerializer`): ¿El `SolicitudService` permite esta transición?
3. **Capa de constantes** (`EstadosSolicitud`): ¿El estado destino está en el conjunto de estados editables por este rol?

---

## 1. Los 5 Estados

| Clave | Label | Rol Gestor | ¿Editable? |
|-------|-------|-----------|-----------|
| `EN_GESTION_MP` | En Gestión (Mesa de Partes) | Mesa de Partes | ✅ Sí |
| `REENVIO_MP` | Reenvío a Mesa de Partes | Mesa de Partes | ✅ Sí |
| `ENVIADO_A_AREA` | Enviado a Área Encargada | Mesa de Partes / Supervisor / Área | ✅ Sí |
| `EN_TRAMITE_AREA` | En Trámite (Área) | Área Encargada | ✅ Sí |
| `CERRADO` | Cerrado | Área Encargada | ❌ No (absorbente) |

### Detalle de cada Estado

#### `EN_GESTION_MP`
- **Descripción**: La solicitud fue creada y está en revisión administrativa en Mesa de Partes.
- **Editable por**: `MESA_DE_PARTES`, `SUPERVISOR`
- **Visible por**: `MESA_DE_PARTES`
- **Usuarios con acceso**: Recepción Mesa de Partes (creador del expediente asociado)

#### `REENVIO_MP`
- **Descripción**: El área devolvió la solicitud a MP por error administrativo (área incorrecta, asignación inválida). MP debe corregir y reenviar.
- **Editable por**: `MESA_DE_PARTES`
- **Visible por**: `SUPERVISOR`, `AREA_ENCARGADA`

#### `ENVIADO_A_AREA`
- **Descripción**: MP redirigió la solicitud al área responsable para gestión de fondo.
- **Editable por**: `MESA_DE_PARTES`, `SUPERVISOR`, `AREA_ENCARGADA`
- **Visible por**: `SUPERVISOR`, `AREA_ENCARGADA`
- **Nota**: Permite al Área Encargada hacer correcciones de última hora antes de iniciar trámite.

#### `EN_TRAMITE_AREA`
- **Descripción**: El área está procesando o revisando la solicitud para su resolución.
- **Editable por**: `AREA_ENCARGADA`
- **Visible por**: `AREA_ENCARGADA`

#### `CERRADO`
- **Descripción**: Proceso finalizado y archivado. Estado absorbente.
- **Editable por**: *(ninguno)*
- **Visible por**: `AREA_ENCARGADA`
- **Transición desde**: `EN_TRAMITE_AREA` (solo desde ahí se puede cerrar)

---

## 2. Transiciones Permitidas

### Matriz de Transiciones

| Estado Actual | → `EN_GESTION_MP` | → `REENVIO_MP` | → `ENVIADO_A_AREA` | → `EN_TRAMITE_AREA` | → `CERRADO` |
|---|---|---|---|---|---|
| `EN_GESTION_MP` | — | ✅ | ✅ | ❌ | ❌ |
| `REENVIO_MP` | ✅ | — | ✅ | ❌ | ❌ |
| `ENVIADO_A_AREA` | ✅ | ✅ | — | ✅ | ❌ |
| `EN_TRAMITE_AREA` | ❌ | ❌ | ❌ | — | ✅ |
| `CERRADO` | ❌ | ❌ | ❌ | ❌ | — (absorbente) |

### Quién puede ejecutar cada transición

| Transición | Rol Autorizado | Validaciones Extra |
|---|---|---|
| `→ EN_GESTION_MP` | Recepción MP, Supervisor | No estar finalizada |
| `→ REENVIO_MP` | Recepción MP | Estado actual en `MESA_DE_PARTES_EDITABLES` |
| `→ ENVIADO_A_AREA` | Recepción MP, Supervisor, Encargado Área | Campos `usuario_asignado`/`area_responsable` deben estar configurados |
| `→ EN_TRAMITE_AREA` | Encargado de Área | El usuario debe ser `usuario_asignado` |
| `→ CERRADO` | Encargado de Área | Estado actual必须是 `EN_TRAMITE_AREA` + solicitud debe tener anexos |

---

## 3. Cómo la Máquina Bloquea las Mutaciones

### 3.1 Blindaje en la Capa de Permisos

Cada clase de permiso hereda de `SafeFieldCheckMixin` y define:

```python
CAMPOS_PERMITIDOS = {"estado", "usuario_asignado", "usuarios_adjuntados", "area_responsable"}
```

Antes de cualquier `UPDATE`/`PATCH`, se invoca `validate_allowed_fields()` que **rechaza** cualquier campo que no esté en `CAMPOS_PERMITIDOS` para ese rol.

### 3.2 Blindaje por Estado Actual

```python
# RecepcionMesaDePartesSolicitudPermission.check_update()
if obj.estado not in EstadosSolicitud.MESA_DE_PARTES_EDITABLES:
    raise PermissionDenied(
        f"No puedes modificar la solicitud cuando está en estado '{obj.estado}'."
    )
```

Esto significa que si una solicitud está en `EN_TRAMITE_AREA`, ni siquiera Recepción MP puede tocarla — el queryset del ViewSet devuelve el objeto, pero el permiso lo bloquea con 403.

### 3.3 Blindaje del Serializer (`validar_edicion`)

```python
# SolicitudMutationSerializer.validate()
if instance:
    Service.validar_edicion(instance, user)

# SolicitudService.validar_edicion()
if solicitud.finalizado:
    if user.is_superuser:
        return  # Excepción de emergencia para superuser
    raise ValidationError("No puedes editar una solicitud que ya está finalizada.")
```

### 3.4 Blindaje de Finalización

Solo el **Encargado de Área** puede marcar `finalizado=True` y solo cuando:

```python
# EncargadoAreaSolicitudPermission.check_update()
if finalizado is True and nuevo_estado != "CERRADO":
    raise PermissionDenied(
        "Solo puedes marcar la solicitud como finalizada cuando el estado es CERRADO."
    )
```

Y además `SolicitudService.validar_finalizacion()` exige que existan anexos:

```python
if not tiene_anexos_bd and not tiene_nuevos_anexos:
    raise ValidationError("No puedes finalizar una solicitud sin evidencia adjunta (anexos).")
```

### 3.5 Inyección Automática de `fecha_cierre`

```python
# SolicitudMutationSerializer.update()
if finalizado_flag is not None:
    instance = SolicitudService.procesar_estado_final(instance, finalizado_flag)

# SolicitudService.procesar_estado_final()
if data_finalizado is True and not solicitud.fecha_cierre:
    solicitud.fecha_cierre = timezone.now()
elif data_finalizado is False:
    solicitud.fecha_cierre = None  # Reapertura
```

---

## 4. Reglas de Visibilidad (¿Quién ve qué?)

| Estado | Recepción MP | Supervisor MP | Encargado Área | Creador Flujos |
|--------|---------------|--------------|----------------|----------------|
| `EN_GESTION_MP` | ✅ | ❌ | ❌ | ✅ |
| `REENVIO_MP` | ❌ | ✅ | ✅ | ✅ |
| `ENVIADO_A_AREA` | ❌ | ✅ | ✅ | ✅ |
| `EN_TRAMITE_AREA` | ❌ | ❌ | ✅ | ✅ |
| `CERRADO` | ❌ | ❌ | ✅ | ✅ |

> **Nota**: `Creador de Flujos` (grupo Django) tiene acceso total por ser rol administrativo del sistema de flujos.

---

## 5. Flujo Visual

```
                                    ┌─────────────────────────────┐
                                    │     EN_GESTION_MP          │
                                    │   (Recepción MP editable)   │
                                    └──────────────┬──────────────┘
                                                   │
                           ┌───────────────────────┼───────────────────────┐
                           │                       │                       │
                           ▼                       ▼                       ▼
              ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
              │   REENVIO_MP     │   │  ENVIADO_A_AREA  │   │  (cierre admin)  │
              │  (MP reedita)    │   │ (MP/Sup/Area ed) │   │                  │
              └────────┬─────────┘   └────────┬─────────┘   └──────────────────┘
                       │                     │
                       │                     │ Si área inicia gestión
                       │                     ▼
                       │         ┌─────────────────────────┐
                       └────────►│    EN_TRAMITE_AREA      │
                                 │  (Solo Encargado edita) │
                                 └────────────┬────────────┘
                                              │
                              ┌───────────────┴───────────────┐
                              │                               │
                              ▼                               ▼
                   ┌──────────────────┐           ┌──────────────────┐
                   │   CON ANEXOS?     │──────────►│  finalize=True    │
                   │   Validación     │   No      │  fecha_cierre=now │
                   └────────┬─────────┘           └─────────┬─────────┘
                            │                             │
                            │ Sí                          │
                            ▼                             ▼
                   ┌─────────────────────────────────────────────┐
                   │              CERRADO (absorbente)           │
                   │   finalizado=True, fecha_cierre=now()      │
                   │   No hay transiciones salientes            │
                   └─────────────────────────────────────────────┘
```

---

## 6. Constantes Relacionadas

```python
# common/utils/constants/solicitudes/estados.py

EstadosSolicitud.MESA_DE_PARTES_EDITABLES       # ['EN_GESTION_MP', 'REENVIO_MP', 'ENVIADO_A_AREA']
EstadosSolicitud.SUPERVISOR_EDITABLES          # ['REENVIO_MP', 'ENVIADO_A_AREA']
EstadosSolicitud.AREA_ENCARGADA_EDITABLES      # ['ENVIADO_A_AREA', 'EN_TRAMITE_AREA']

# Verificación programática
EstadosSolicitud.puede_editar_por("EN_TRAMITE_AREA", "AREA_ENCARGADA")  # True
EstadosSolicitud.puede_editar_por("EN_TRAMITE_AREA", "MESA_DE_PARTES")  # False → 403
```
