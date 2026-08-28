# DatosSolicitanteSection

**Archivo**: `frontend/src/app/dashboard/expedientes/_components/forms/DatosSolicitanteSection.tsx`

**Propósito**: Renderiza dinámicamente los campos de identificación del solicitante según el tipo de persona seleccionado (`NATURAL`, `JURIDICA`, `COLEGIADO`). Usa `react-hook-form` `watch` para detectar cambios de tipo en tiempo real.

---

## 1. Arquitectura de Renderizado

```
DatosSolicitanteSection
└── Grid 12 columnas (Tailwind)
    ├── RadioGroup: tipo_persona (NATURAL | JURIDICA | COLEGIADO)
    ├── [NATURAL] → DNI + Nombres + Apellidos
    ├── [JURIDICA] → RUC + Razón Social + mini-sección Representante (DNI + Nombre)
    ├── [COLEGIADO] → CIP + Nombres + Apellidos
    └── [COMUN] → Teléfono + Correo
```

**Patrón**: Conditional rendering con JSX ternario `tipoPersona === "NATURAL" && (...)`. Cada bloque retorna un grupo de `CardFieldWrapper` que envuelven `Input` de shadcn/ui.

---

## 2. Tipo de Persona — Campos por Caso

### NATURAL
| Campo | Zod | MaxLength | Grid |
|---|---|---|---|
| `dni` | `z.string()` | 8 | `col-span-12 md:col-span-4` |
| `nombres` | `z.string()` | — | `col-span-12 md:col-span-4` |
| `apellidos` | `z.string()` | — | `col-span-12 md:col-span-4` |

### JURIDICA
| Campo | Zod | MaxLength | Grid |
|---|---|---|---|
| `ruc` | `z.string()` | 11 | `col-span-12 md:col-span-4` |
| `razon_social` | `z.string()` | — | `col-span-12 md:col-span-8` |
| *(mini-sección)* | | | |
| `dni` (repr.) | `z.string()` | 8 | `col-span-12 md:col-span-3` |
| `nombres` (repr.) | `z.string()` | — | `col-span-12 md:col-span-9` |

### COLEGIADO
| Campo | Zod | MaxLength | Grid |
|---|---|---|---|
| `cip` | `z.string()` | 6 | `col-span-12 md:col-span-2` |
| `nombres` | `z.string()` | — | `col-span-12 md:col-span-5` |
| `apellidos` | `z.string()` | — | `col-span-12 md:col-span-5` |

---

## 3. Campos Comunes (siempre visibles)

Se renderizan **al final** del grid, fuera de los bloques condicionales:

- `telefono` — `col-span-12 md:col-span-6`, `type="text"` (no `type="tel"`)
- `correo` — `col-span-12 md:col-span-6`, `type="email"`

---

## 4. Reutilización de Nombres de Campo

> **⚠️ Limitación known**: Los campos `dni`, `nombres`, `apellidos` se reutilizan en los 3 tipos de persona. En modo `JURIDICA`, el `dni` representa al representante; en `NATURAL` y `COLEGIADO` es el propio solicitante.

Esto es una decisión de schema (no hay campos `dni_representante` ni `nombres_representante` separados), lo que significa que el mismo nombre de campo sirve para datos semanticamente distintos según el tipo de persona. El schema Zod (`ExpedienteCreateSchema`) no diferencia la validación por `tipo_persona`.

---

## 5. Validación Visual

Cada `Input` se registra directamente con `react-hook-form` via `register`:

```typescript
<Input {...register("dni")} maxLength={8} placeholder="Ingrese DNI" />
```

El error se pasa a `CardFieldWrapper` que lo renderiza si existe:

```typescript
error={errors.dni}
```

**No hay validación Zod a nivel de campo individual más allá de `maxLength`** en el `Input`. La validación estructural (tipos de persona vs. campos requeridos) no está enforced por el schema.

---

## 6. Props

| Prop | Tipo | Descripción |
|---|---|---|
| `form` | `UseFormReturn<ExpedienteFormData>` | Instancia completa del form — se pasa el form entero para que `DatosSolicitanteSection` pueda hacer `watch`, `register`, `setValue`, etc. |

No destructura `control` directamente; recibe el form entero porque internamente necesita `watch("tipo_persona")` y múltiples `register`.

---

## 7. Estructura de Grid

```tsx
<div className="w-full grid grid-cols-12 gap-x-4 gap-y-4">
  {/* Selector tipo_persona: col-span-12 */}
  {/* Bloque condicional: col-span-12 + elementos internos */}
  {/* Campos comunes: col-span-12 */}
</div>
```

Se usa `grid-cols-12` de Tailwind para que los `col-span-*` internos funcionen correctamente. Anteriormente faltaba esta clase, lo que causaba que los `col-span` no tuvieran efecto.
