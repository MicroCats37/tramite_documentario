// genericForm/inputs/InputSelectArea.tsx
// Smart Field para selección de área institucional con búsqueda.
// Usa useController de RHF + useAreas() internamente.
// No hardcodea validaciones — Zod evalúa.

"use client";

import type React from "react";
import { useController } from "react-hook-form";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { useAreas } from "@/features/tramites/hooks/useAreas";
import type { InputComponentProps } from "./types";

/**
 * InputSelectArea — Smart Field para seleccionar un área institucional con búsqueda.
 *
 * Internamente hace fetch a GET /api/areas usando useAreas().
 * Muestra solo áreas activas (filtrado en useAreas).
 * Validación VIA Zod: el schema debe incluir .min(1) o .uuid() para el campo.
 */
export const InputSelectArea: React.FC<InputComponentProps> = ({
  field,
  control,
  error,
  id,
  // register es parte de InputComponentProps pero no se usa — el Smart Field usa
  // useController internamente (igual que InputSelect/InputSearchableSelect).
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  register: _register,
}) => {
  const { areas, isLoading, isError } = useAreas();

  const {
    field: rhfField,
    fieldState: { error: rhfError },
  } = useController({
    name: field.name,
    control,
  });

  // Error message: priorizar el error de RHF (validación), luego el error genérico.
  const errorMessage = rhfError?.message ?? error?.message;

  // Transformar las áreas al shape de SearchableSelectOption
  const options = areas.map((area) => ({
    value: area.id,
    label: area.descripcion ? `${area.nombre} — ${area.descripcion}` : area.nombre,
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
          ? "Cargando áreas..."
          : isError
            ? "Error al cargar áreas"
            : (field.placeholder ?? "Buscar área...")
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