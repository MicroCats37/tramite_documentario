# Tablas base: Expediente y Solicitud

## 1. Tabla `Expediente`

**Intención:** almacenar la información objetiva y documental que ingresa al sistema.

`Expediente` no debe contener lógica de flujo, áreas responsables ni usuarios asignados. Su responsabilidad es describir qué ingresó al sistema y conservar la información documental del expediente.

| Campo | Tipo conceptual | Obligatorio | Descripción |
|---|---|---:|---|
| `id` | UUID | Sí | PK heredada del `BaseModel`. |
| `id_publico` | String | Sí | Código visible del expediente. Ej.: `LIMA-2026-XXXX`. |
| `tipo_persona` | Enum/String | Sí | Natural, jurídica, colegiado, etc. |
| `dni` | String | No | Documento para persona natural. |
| `ruc` | String | No | Documento para persona jurídica. |
| `cip` | String | No | Código CIP cuando corresponda. |
| `razon_social` | String | No | Razón social de persona jurídica. |
| `nombres` | String | No | Nombres del interesado o representante. |
| `apellidos` | String | No | Apellidos del interesado o representante. |
| `telefono` | String | No | Teléfono de contacto. |
| `correo` | String | No | Correo de contacto. |
| `tipo_documento` | Enum/String | Sí | Tipo de documento ingresado. |
| `numero_documento` | String | Sí | Número del documento administrativo. |
| `numero_folios` | Integer | Sí | Número de folios recibidos. |
| `asunto` | String | Sí | Asunto principal del expediente. |
| `archivo_principal` | File | Sí | Documento principal ingresado. |
| `observaciones` | Text | No | Información adicional. |
| `fecha_registro` | DateTime | Sí | Fecha real o histórica en la que ingresó el expediente. Importante para migración Legacy. |
| `creado_por` | FK User | Sí | Usuario que registró el expediente. |
| `modificado_por` | FK User | No | Último usuario que realizó una modificación funcional. |
| `created_at` | DateTime | Sí | Heredado del `BaseModel`. Fecha técnica de creación de la fila. |
| `updated_at` | DateTime | Sí | Heredado del `BaseModel`. Última modificación técnica. |

### Relaciones de `Expediente`

```text
Expediente
    |
    +-- 1:N ExpedienteArchivoAnexo
    |
    +-- N:M Expediente
    |      antecedentes / consecuentes
    |
    +-- 1:1 Solicitud
```

### Regla importante de fechas

`fecha_registro` y `created_at` no representan lo mismo.

```text
fecha_registro = fecha real del negocio
created_at     = fecha técnica de creación en la nueva base
```

Ejemplo al migrar información Legacy:

```text
fecha_registro = 2022-04-15
created_at     = 2026-08-23
```

Esto es correcto y debe mantenerse así para no perder el contexto histórico real.

---

# 2. Tabla `Solicitud`

**Intención:** representar el trámite o caso global asociado al expediente.

La `Solicitud` conserva el ciclo de vida global del trámite, pero ya no debería contener directamente el área responsable ni los usuarios que trabajan en ella.

La participación de áreas y usuarios se mueve al nuevo modelo:

```text
Solicitud
    |
    +-- SolicitudAsignacion
            |
            +-- SolicitudAsignacionPeriodo
                    |
                    +-- SolicitudAsignacionUsuario
```

| Campo | Tipo conceptual | Obligatorio | Descripción |
|---|---|---:|---|
| `id` | UUID | Sí | PK heredada del `BaseModel`. |
| `id_publico` | String | Sí | Código visible de la solicitud, si se desea conservar independiente. |
| `expediente` | OneToOne Expediente | Sí | Expediente que origina el trámite. |
| `estado` | Enum/String | Sí | Estado global de la solicitud. |
| `prioridad` | Enum/String | Sí | Ej.: normal, alta, crítica. |
| `fecha_registro` | DateTime | Sí | Fecha real o histórica en que nació la solicitud o trámite. |
| `fecha_limite` | DateTime | No | Fecha límite global del trámite, si corresponde. |
| `fecha_cierre` | DateTime | No | Fecha real en que la solicitud se cerró globalmente. |
| `creado_por` | FK User | Sí | Usuario que creó el trámite. |
| `modificado_por` | FK User | No | Último usuario que realizó una modificación funcional. |
| `observacion` | Text | No | Observaciones generales del trámite. |
| `created_at` | DateTime | Sí | Heredado del `BaseModel`. Fecha técnica. |
| `updated_at` | DateTime | Sí | Heredado del `BaseModel`. Última modificación técnica. |

## Campos que salen de la `Solicitud` Legacy

Los siguientes conceptos ya no deberían vivir directamente en `Solicitud`:

| Campo Legacy | Nuevo destino |
|---|---|
| `area_responsable` | `SolicitudAsignacion` |
| `usuario_asignado` | `SolicitudAsignacionUsuario` |
| `usuarios_adjuntos` | `SolicitudAsignacionUsuario`, usando roles si posteriormente se requieren |

Esto evita que la `Solicitud` vuelva a concentrar el flujo operativo de áreas y usuarios.

## Campo `finalizado`

Debe revisarse si realmente es necesario conservarlo.

Si:

```text
estado = FINALIZADA
```

ya significa exactamente que la solicitud terminó, entonces un campo adicional:

```text
finalizado = True
```

duplica información.

La recomendación es mantener una sola fuente de verdad siempre que sea posible.

### Relaciones de `Solicitud`

```text
Solicitud
    |
    +-- 1:1 Expediente
    |
    +-- 1:N SolicitudArchivoAnexo
    |
    +-- 1:N ComentarioSolicitud
    |
    +-- 1:N SolicitudEstadoHistorial
    |
    +-- 1:N SolicitudAsignacion
            |
            +-- Area A
            +-- Area B
            +-- Area C
```

---

# 3. Separación conceptual

```text
EXPEDIENTE
|
| Información objetiva
| Persona / empresa
| Documento
| Asunto
| Archivos
| Fecha real de ingreso
|
+-- 1:1
     |
     v
SOLICITUD
|
| Trámite global
| Estado global
| Prioridad
| Plazos
| Fecha de cierre
|
+-- 1:N
     |
     v
SOLICITUD_ASIGNACION
|
+-- Arquitectura
+-- Estructuras
+-- Eléctrica
```

La intención de cada nivel es:

```text
Expediente
= qué ingresó al sistema

Solicitud
= qué trámite se abrió con lo ingresado

SolicitudAsignacion
= qué áreas participan en ese trámite
```

---

# 4. Consideración para migración Legacy

Las fechas técnicas heredadas de `BaseModel` no deben utilizarse para reconstruir la historia administrativa.

Por ejemplo:

```text
Solicitud histórica:
fecha_registro = 2021-09-10
created_at     = 2026-08-23
```

La primera fecha permite mantener:

- antigüedad real;
- tiempos históricos;
- reportes por año;
- métricas del trámite;
- orden cronológico de los datos Legacy.

La segunda fecha solamente informa cuándo la fila fue incorporada a la nueva plataforma.
