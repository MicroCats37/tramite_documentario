# Referencia de Endpoints Legacy (V1)

Este documento contiene el mapeo exacto de las rutas de la versión anterior. Sirve como referencia base para saber qué funcionalidades deben ser migradas y refactorizadas para la V2.

## 1. Módulo: Expedientes (`/api/expedientes/`)
| Método | Endpoint | Acción | Descripción |
|--------|----------|--------|-------------|
| GET | `/api/expedientes/` | `list` | Lista expedientes (filtrado por usuario) |
| POST | `/api/expedientes/` | `create` | Crea expediente con anexos |
| GET | `/api/expedientes/{uuid}/` | `retrieve` | Detalle de expediente |
| PUT/PATCH | `/api/expedientes/{uuid}/` | `update/partial_update` | Actualiza expediente |
| DELETE | `/api/expedientes/{uuid}/` | `destroy` | Elimina expediente |
| GET | `/api/expedientes/creadas/` | `creadas` | Expedientes creados por el usuario actual |
| GET | `/api/expedientes/creadas-sin-solicitud/` | `creadas_sin_solicitud` | Expedientes sin solicitud asociada |

**ExpedienteArchivoAnexo:** `/api/expedientes-archivo-anexo/` (CRUD estándar)

## 2. Módulo: Solicitudes (`/api/solicitudes/`)
| Método | Endpoint | Acción | Descripción |
|--------|----------|--------|-------------|
| GET | `/api/solicitudes/` | `list` | Lista solicitudes |
| POST | `/api/solicitudes/` | `create` | Crear nueva solicitud |
| GET | `/api/solicitudes/{uuid}/` | `retrieve` | Detalle |
| PUT/PATCH | `/api/solicitudes/{uuid}/` | `update/partial_update` | Actualización |
| DELETE | `/api/solicitudes/{uuid}/` | `destroy` | **Bloqueado (siempre retorna 403)** |
| GET | `/api/solicitudes/asignadas/` | `asignadas` | Donde `usuario_asignado = request.user` |
| GET | `/api/solicitudes/creadas/` | `creadas` | Donde `expediente.creado_por = request.user` |
| GET | `/api/solicitudes/mi-area/` | `mi_area` | Solicitudes del área del usuario |
| GET | `/api/solicitudes/adjuntadas/` | `adjuntadas` | Donde el usuario es colaborador |

**Comentarios:** `/api/comentarios-solicitud/` (list, create, retrieve — updates/deletes bloqueados)

## 3. Módulo: Usuarios/Auth (`/api/`)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/login/` | Login JWT (retorna access + refresh token) |
| POST | `/api/logout/` | Logout (blacklist refresh token) |
| GET | `/api/me/` | Perfil del usuario autenticado |
| GET | `/api/pendientes/` | Solicitudes pendientes (asignadas + adjuntadas) |
| GET | `/api/perfil-usuario/` | PerfilUsuario (CRUD, solo lectura) |
| GET | `/api/areas/` | Catálogo de áreas (CRUD, solo lectura) |

## 4. Módulo: Liquidaciones (`/api/liquidaciones/`)
| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/liquidaciones/habilitacion-urbana/tarifas/vigentes` | Tarifas activas para HU |
| POST | `/api/liquidaciones/habilitacion-urbana/cotizar` | Calcular cotización (sin persistencia) |
| POST | `/api/liquidaciones/habilitacion-urbana/nueva-liquidacion/primera-revision` | Crear liquidación (sí persiste) |

## Grupos de Permisos Identificados (V1)
- `Recepcion Mesa de Partes` — Crear/modificar expedientes y solicitudes en MP
- `Supervisor Mesa de Partes` — Supervisar y editar estados
- `Encargado de Área` — Gestionar solicitudes de su área
- `Creador de Flujos` — Acceso completo sin restricciones de estado