# SmartFileField

**Archivo**: `frontend/src/app/dashboard/expedientes/_components/forms/SmartFileField.tsx`

**Propósito**: Componente genérico de carga de archivos que funciona con `react-hook-form`. Detecta automáticamente si el valor actual es un `File` (nuevo archivo sin guardar), un `string` (URL existente del backend), o `null` (vacío). Cambia su UI según el estado.

---

## 1. Tipos de Estado

```
value = null         → Modo "carga" (Input file)
value = File         → Modo "nuevo archivo" (Badge verde + preview del nombre)
value = string (URL) → Modo "existente" (Vista previa con enlace + botón Cambiar)
```

---

## 2. Detección de Tipo

```typescript
const isFile = (value: unknown): value is File => {
  return (
    typeof File !== "undefined" &&
    typeof value === "object" &&
    value !== null &&
    value instanceof File
  );
};

const isExistingUrl = typeof value === "string" && value.length > 0;
const isNewFile = isFile(value);
```

Se usa type guard personalizado (`isFile`) en lugar de `instanceof File` directamente en el prop para evitar problemas con entornos donde `File` podría no estar definido (SSR早期的 edge cases).

---

## 3. Caso A — URL Existente (Modo Edición)

```tsx
{isExistingUrl && (
  <div className="flex items-center gap-3 p-3 border rounded-md bg-muted/30">
    <FileText icon />
    <div>
      <p className="text-sm font-medium truncate">Archivo actual del sistema</p>
      <a href={value} target="_blank" rel="noopener noreferrer">
        <Eye icon /> Ver documento
      </a>
    </div>
    <Button onClick={() => onChange(null)}>Cambiar</Button>
  </div>
)}
```

- Muestra un enlace para visualizar el archivo existente.
- El botón "Cambiar" establece el valor a `null`, lo que revela el input de carga.
- **No elimina el archivo del backend** — solo limpia el valor local. El submit handler de `ExpedienteForm` elimina la URL del payload si no se reemplazó.

---

## 4. Caso B — Carga de Nuevo Archivo

```tsx
{!isExistingUrl && (
  <div className="space-y-3">
    <Input
      type="file"
      ref={ref}
      onChange={(e) => {
        const file = e.target.files?.[0];
        onChange(file || null);
      }}
    />
    {isNewFile && (
      <div className="flex items-center justify-between p-2 bg-green-50 ...">
        <span><UploadCloud /> {value.name}</span>
        <Button type="button" variant="ghost" size="icon" onClick={() => onChange(null)}>
          <Trash2 />
        </Button>
      </div>
    )}
  </div>
)}
```

- Si `isNewFile` es `true`, muestra una barra verde con el nombre del archivo y un botón para eliminarlo.
- `onChange(null)` vuelve al estado "vacío" y permite seleccionar otro archivo.

---

## 5. Interfaz Genérica `<T extends FieldValues>`

```typescript
interface SmartFileFieldProps<T extends FieldValues> {
  control: Control<T>;
  name: Path<T>;
  label?: string;
  description?: string;
  error?: any;
}
```

- **Genérico**: funciona con cualquier form que extienda `FieldValues`, no solo `ExpedienteFormData`.
- `name: Path<T>` asegura en TypeScript que el nombre pasado corresponde a un campo real del form.
- `control` viene de `useForm()` y se pasa al `useController` interno.

---

## 6. Integración con ExpedienteForm

```typescript
archivo_principal: (methods) => (
  <SmartFileField
    control={methods.control}
    name="archivo_principal"
    label={isEditing ? "Reemplazar Archivo Principal" : "Archivo Principal del Expediente"}
    error={(methods.formState.errors as any).archivo_principal}
  />
),
```

- Se pasa `methods.control` (no `methods` completo).
- El `error` se castea a `any` porque `formState.errors` está tipado como `DeepMap` genérico.

---

## 7. Limitaciones Conocidas

1. **Un solo archivo**: El `Input type="file"` no tiene `multiple`; solo permite seleccionar un archivo a la vez.
2. **Sin preview del contenido**: Solo muestra el nombre del archivo, no una vista previa para PDFs o imágenes.
3. **Sin validación de tipo ni tamaño de archivo**: No hay restricción en el componente sobre MIME type o tamaño máximo. La validación (si existe) debe venir del schema Zod o del backend.
4. **Reutilización de `dni`/`nombres`/`apellidos`**: Este componente no tiene relación con ese problema; es solo para archivos.
