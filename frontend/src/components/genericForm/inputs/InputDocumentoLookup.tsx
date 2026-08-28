// genericForm/inputs/InputDocumentoLookup.tsx
"use client";

import { Loader2, Search } from "lucide-react";
import { useRef } from "react";
import { useController, useFormContext, useWatch } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { notify } from "@/errors";
import {
  useDocumentoLookup,
  type DocumentoConsultaData,
} from "@/features/entidades/hooks/useConsultaExterna";
import { cn } from "@/lib/utils";
import type { InputComponentProps } from "./types";

/** Field names config — tells the component which RHF fields to write after lookup. */
export interface DocumentoLookupFieldNames {
  [key: string]: string | undefined;
  /** Identifica el campo del número de documento en el form (ej. "dni" o "ruc"). */
  numero_documento: string;
  /** Campo donde se escribe la razón social (para RUC). */
  razon_social: string;
  /** Campo donde se escribe el apellido (solo para DNI, si está en el schema). */
  apellidos?: string;
  /** Campo donde se escribe el nombre (solo para DNI, si está en el schema). */
  nombres?: string;
}

/** Default field names matching the Solicitud schema. */
const DEFAULT_FIELD_NAMES: DocumentoLookupFieldNames = {
  numero_documento: "dni",
  razon_social: "razon_social",
  nombres: "nombres",
  apellidos: "apellidos",
};

interface InputDocumentoLookupProps extends InputComponentProps {}

/**
 * Smart Field for document lookup (DNI → nombres/apellidos, RUC → razon_social).
 *
 * Follows the Smart Field pattern:
 * - Uses useController for the numero_documento field
 * - Does NOT validate (Zod handles it)
 * - Accepts hideErrorMessage (provided by GenericInput wrapper)
 * - Anti-loop via isInternalUpdate ref
 *
 * UI: document number input + "Buscar" button. When lookup succeeds:
 *   - DNI (8 digits): splits razon_social ("APELLIDOS, NOMBRES") → writes nombres + apellidos
 *   - RUC (11 digits): writes razon_social directly
 *
 * Usage in STEP_1_FIELDS:
 *   { name: "dni", label: "DNI", type: "documento-lookup",
 *     fieldNames: { tipo_documento: "DNI", numero_documento: "dni", razon_social: "razon_social", nombres: "nombres", apellidos: "apellidos" },
 *     containerClassName: "md:col-span-12" }
 */
export const InputDocumentoLookup: React.FC<InputDocumentoLookupProps> = ({
  field: rawField,
  control,
  error,
  id,
  hideErrorMessage,
}) => {
  // Resolve fieldNames from the field prop (passed via FormField.fieldNames in STEP_1_FIELDS)
  const fieldNames: DocumentoLookupFieldNames = {
    ...DEFAULT_FIELD_NAMES,
    ...(rawField.fieldNames as DocumentoLookupFieldNames | undefined),
  };

  // isRUC mode: RUC lookup writes razon_social; DNI lookup writes nombres + apellidos
  const isRUC = fieldNames.numero_documento === "ruc";

  // useFormContext: para que setValue funcione dentro del form real (no crea uno nuevo).
  const { setValue } = useFormContext();
  const documentoLookup = useDocumentoLookup();
  const isConsulting = documentoLookup.isPending;

  // ── useController for the numero_documento field (local input state) ──────────
  const numeroCtrl = useController({
    name: fieldNames.numero_documento,
    control,
    defaultValue: "",
  });

  // ── Watch the result fields so they re-render when set externally ────────────
  const watchedNombres = fieldNames.nombres
    ? (useWatch({ control, name: fieldNames.nombres }) as string | undefined)
    : undefined;
  const watchedApellidos = fieldNames.apellidos
    ? (useWatch({ control, name: fieldNames.apellidos }) as string | undefined)
    : undefined;
  const watchedRazonSocial = useWatch({
    control,
    name: fieldNames.razon_social,
  }) as string | undefined;

  // Anti-loop ref: prevents the sync effect from firing when we update from inside
  const isInternalUpdate = useRef(false);

  const maxLength = isRUC ? 11 : 8;

  const handleNumeroChange = (val: string) => {
    if (!/^\d*$/.test(val)) return;
    if (val.length > maxLength) return;
    isInternalUpdate.current = true;
    numeroCtrl.field.onChange(val);
  };

  const isLookupValid =
    (numeroCtrl.field.value ?? "").trim().length === maxLength;

  /**
   * Escribe los campos del form con los datos del documento.
   * Para DNI: split "APELLIDOS, NOMBRES" → apellidos y nombres.
   * Para RUC: escribe solo razon_social.
   * NO toca `tipo_documento` (es el tipo de documento del TRÁMITE, no del documento de identidad).
   */
  const setAllFields = (numDoc: string, razonSocial: string) => {
    isInternalUpdate.current = true;
    // Re-asegurar el número (por si el usuario borró y consultó con un valor anterior)
    setValue(fieldNames.numero_documento, numDoc, { shouldValidate: true });

    if (isRUC) {
      setValue(fieldNames.razon_social, razonSocial, { shouldValidate: true });
    } else {
      // DNI: split "APELLIDOS, NOMBRES" → apellidos y nombres
      if (fieldNames.apellidos && fieldNames.nombres) {
        const parts = razonSocial.split(", ");
        if (parts.length === 2) {
          setValue(fieldNames.apellidos, parts[0], { shouldValidate: true });
          setValue(fieldNames.nombres, parts[1], { shouldValidate: true });
        } else {
          // Si el formato no incluye la coma, va todo a razon_social
          setValue(fieldNames.razon_social, razonSocial, { shouldValidate: true });
        }
      } else {
        // Si el schema no tiene campos de nombre separados, va a razon_social
        setValue(fieldNames.razon_social, razonSocial, { shouldValidate: true });
      }
    }
  };

  const handleLookup = async () => {
    const num = (numeroCtrl.field.value ?? "").trim();
    if (!num) {
      notify.error("Ingresa el número de documento a consultar");
      return;
    }

    const expectedLen = isRUC ? 11 : 8;
    if (num.length !== expectedLen) {
      notify.error(
        isRUC
          ? "El RUC debe tener 11 dígitos"
          : "El DNI debe tener 8 dígitos",
      );
      return;
    }

    try {
      const result = await documentoLookup.mutateAsync(num);
      if (result) {
        const data = result as DocumentoConsultaData;
        setAllFields(num, data.razon_social || "");
        notify.success("Datos del documento cargados");
      }
    } catch {
      // Error toast handled by useDocumentoLookup
    }
  };

  return (
    <div className="space-y-3">
      {/* ── Document number input + Buscar button ──────────────────────────── */}
      <div className="flex gap-2 min-w-0">
        <div className="flex-1 min-w-0">
          <Input
            id={id}
            type="text"
            inputMode="numeric"
            pattern="[0-9]*"
            value={numeroCtrl.field.value ?? ""}
            onChange={(e) => handleNumeroChange(e.target.value)}
            onBlur={numeroCtrl.field.onBlur}
            ref={numeroCtrl.field.ref}
            name={numeroCtrl.field.name}
            placeholder={isRUC ? "Ej: 20456789012" : "Ej: 87654321"}
            className={cn(
              "h-10 rounded-xl",
              error && "border-destructive focus-visible:ring-destructive",
            )}
            aria-invalid={!!error}
          />
        </div>
        <Button
          type="button"
          size="default"
          onClick={handleLookup}
          disabled={isConsulting || !isLookupValid}
          className="h-10 rounded-xl gap-2 shrink-0"
          aria-label={isRUC ? "Buscar RUC" : "Buscar DNI"}
        >
          {isConsulting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Search className="h-4 w-4" />
          )}
          Buscar
        </Button>
      </div>

      {/* ── Result fields (auto-fill from lookup) ────────────────────────── */}
      {!isRUC && fieldNames.nombres && fieldNames.apellidos && (
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5 min-w-0">
            <Label
              htmlFor={`${id}-nombres`}
              className="text-primary font-semibold text-sm"
            >
              Nombres
            </Label>
            <Input
              id={`${id}-nombres`}
              type="text"
              value={watchedNombres ?? ""}
              onChange={(e) => {
                isInternalUpdate.current = true;
                setValue(fieldNames.nombres!, e.target.value);
              }}
              placeholder="Nombres"
              className="h-10 rounded-xl"
            />
          </div>
          <div className="space-y-1.5 min-w-0">
            <Label
              htmlFor={`${id}-apellidos`}
              className="text-primary font-semibold text-sm"
            >
              Apellidos
            </Label>
            <Input
              id={`${id}-apellidos`}
              type="text"
              value={watchedApellidos ?? ""}
              onChange={(e) => {
                isInternalUpdate.current = true;
                setValue(fieldNames.apellidos!, e.target.value);
              }}
              placeholder="Apellidos"
              className="h-10 rounded-xl"
            />
          </div>
        </div>
      )}

      {isRUC && (
        <div className="space-y-1.5 min-w-0">
          <Label
            htmlFor={`${id}-razon`}
            className="text-primary font-semibold text-sm"
          >
            Razón Social
          </Label>
          <Input
            id={`${id}-razon`}
            type="text"
            value={watchedRazonSocial ?? ""}
            onChange={(e) => {
              isInternalUpdate.current = true;
              setValue(fieldNames.razon_social, e.target.value);
            }}
            placeholder="Nombre de la empresa"
            className="h-10 rounded-xl"
          />
        </div>
      )}

      {/* Error message — rendered only if hideErrorMessage is false */}
      {!hideErrorMessage && error && (
        <p className="text-sm text-destructive font-medium">
          {error.message}
        </p>
      )}
    </div>
  );
};
