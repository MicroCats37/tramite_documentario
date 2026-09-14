// genericForm/inputs/InputSelectTipoDocumento.tsx
// Smart Field para selección de tipo de documento con búsqueda.
// Usa useController de RHF + useTiposDocumento() internamente.
// No hardcodea validaciones — Zod evalúa.

"use client";

import type React from "react";
import { useController } from "react-hook-form";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { useTiposDocumento } from "@/features/tramites/hooks/useTiposDocumento";
import type { InputComponentProps } from "./types";

/**
 * InputSelectTipoDocumento — Smart Field para seleccionar un tipo de documento con búsqueda.
 *
 * Internamente hace fetch a GET /api/tipos-documento usando useTiposDocumento().
 * Muestra todos los tipos de documento del catálogo.
 * Validación VIA Zod: el schema debe incluir .uuid() o .min(1) para el campo.
 */
export const InputSelectTipoDocumento: React.FC<InputComponentProps> = ({
  field,
  control,
  error,
  id,
  // register es parte de InputComponentProps pero no se usa — el Smart Field usa
  // useController internamente (igual que InputSelect/InputSearchableSelect).
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  register: _register,
}) => {
  const { tiposDocumento, isLoading, isError } = useTiposDocumento();

  const {
    field: rhfField,
    fieldState: { error: rhfError },
  } = useController({
    name: field.name,
    control,
  });

  // Error message: priorizar el error de RHF (validación), luego el error genérico.
  const errorMessage = rhfError?.message ?? error?.message;

  // Transformar los tipos de documento al shape de SearchableSelectOption
  const options = tiposDocumento.map((td) => ({
    value: td.id,
    label: td.descripcion
      ? `${td.nombre} — ${td.descripcion}`
      : td.nombre,
  }));

  return (
    <SearchableSelect
      id={id}
      label={field.label}
      value={(rhfField.value as string | null) ?? null}
      onValueChange={(value) => {
        rhfField.onChange(value);
        rhfField.onBlur();
      }}
      options={options}
      placeholder={
        isLoading
          ? "Cargando tipos de documento..."
          : isError
            ? "Error al cargar tipos de documento"
            : (field.placeholder ?? "Buscar tipo de documento...")
      }
      disabled={field.disabled || isLoading}
      error={!!rhfError || !!error}
      errorMessage={errorMessage}
      // hideErrorMessage: el GenericInput wrapper ya renderiza el error.
      hideErrorMessage
      showLabel={false}
    />
  );
};
