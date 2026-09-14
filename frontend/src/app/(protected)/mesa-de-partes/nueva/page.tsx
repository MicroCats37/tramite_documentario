/**
 * Crear Trámite — formulario de creación completa.
 * Ruta: /mesa-de-partes/nueva
 *
 * Stepper de 7 pasos usando GenericForm + secciones .app-card con Next/Back.
 * Envía multipart/form-data a POST /api/solicitudes/crear-completo
 * vía useCrearTramite() (buildApiPayload interno).
 *
 * Pasos:
 *  1. Tipo de persona
 *  2. Datos del interesado
 *  3. Datos del documento
 *  4. Archivos (principal + anexos)
 *  5. Prioridad
 *  6. Distribución de áreas (lista dinámica)
 *  7. Revisión y envío
 */
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  FileText,
  Loader2,
  Plus,
  Send,
  Trash2,
  User,
  Users,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useId, useState } from "react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { InputSelectTipoDocumento } from "@/components/genericForm/inputs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { PageWrapper } from "@/components-app/page";
import { useCrearTramite } from "@/features/tramites/hooks/useTramites";
import { useTiposDocumento } from "@/features/tramites/hooks/useTiposDocumento";
import {
  type ArchivoData,
  type AreaDistribucionData,
  type CreateTramiteData,
  CreateTramiteSchema,
} from "@/features/tramites/schemas/tramite.schema";
import {
  PRIORIDAD_SOLICITUD,
  type PrioridadSolicitud,
  TIPO_PARTICIPACION,
  TIPO_PERSONA,
  type TipoParticipacion,
  type TipoPersona,
} from "@/shared/constants/tramite.tokens";

// ── Constants ─────────────────────────────────────────────────────────────────

const TOTAL_STEPS = 7;

const STEP_LABELS = [
  "Tipo de persona",
  "Datos del interesado",
  "Datos del documento",
  "Archivos",
  "Prioridad",
  "Distribución de áreas",
  "Revisión",
] as const;

// ── Placeholder areas ─────────────────────────────────────────────────────────

/**
 * Placeholder para el catálogo de áreas activas.
 * TODO: reemplazar con chamada real a GET /api/areas cuando el endpoint exista.
 */
const PLACEHOLDER_AREAS = [
  { id: "00000000-0000-0000-0000-000000000001", nombre: "Área de Trámites" },
  { id: "00000000-0000-0000-0000-000000000002", nombre: "Área Legal" },
  { id: "00000000-0000-0000-0000-000000000003", nombre: "Área de Gestión" },
  { id: "00000000-0000-0000-0000-000000000004", nombre: "Secretaría" },
] as const;

// ── Default form values ───────────────────────────────────────────────────────

const defaultValues: CreateTramiteData = {
  prioridad: "MEDIA",
  observacion: null,
  areas_distribucion: [],
  expediente: {
    tipo_persona: "NATURAL",
    dni: null,
    ruc: null,
    cip: null,
    razon_social: null,
    nombres: null,
    apellidos: null,
    correo: null,
    telefono: null,
    tipo_documento_id: null,
    numero_documento: null,
    numero_folios: 0,
    asunto: "",
    observaciones: null,
    archivos: {
      principal: [],
      anexo: [],
    },
  },
};

// ── Stepper Progress ───────────────────────────────────────────────────────────

interface StepperProps {
  currentStep: number;
  labels: readonly string[];
  onStepClick?: (step: number) => void;
  completedSteps: number[];
}

function Stepper({
  currentStep,
  labels,
  onStepClick,
  completedSteps,
}: StepperProps) {
  return (
    <div className="flex items-center gap-1 overflow-x-auto pb-2">
      {labels.map((label, idx) => {
        const stepNum = idx + 1;
        const isCompleted = completedSteps.includes(stepNum);
        const isCurrent = stepNum === currentStep;
        const isClickable = isCompleted || stepNum === 1;

        return (
          <div key={stepNum} className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => isClickable && onStepClick?.(stepNum)}
              disabled={!isClickable}
              className={`
                flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium
                transition-colors whitespace-nowrap
                ${isClickable ? "cursor-pointer" : "cursor-default opacity-50"}
                ${isCurrent ? "bg-primary text-primary-foreground" : ""}
                ${isCompleted && !isCurrent ? "success-bg-subtle success-text" : ""}
                ${!isCurrent && !isCompleted ? "bg-muted text-muted-foreground hover:bg-muted/80" : ""}
              `}
              aria-current={isCurrent ? "step" : undefined}
            >
              <span className="flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-bold border shrink-0">
                {isCompleted ? (
                  <CheckCircle2 className="h-3.5 w-3.5" />
                ) : (
                  stepNum
                )}
              </span>
              <span className="hidden sm:inline">{label}</span>
            </button>
            {idx < labels.length - 1 && (
              <div className={`w-4 h-px bg-border mx-0.5 shrink-0`} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Field components ───────────────────────────────────────────────────────────

interface FieldProps {
  label: string;
  error?: string;
  required?: boolean;
  children: React.ReactNode;
}

function Field({ label, error, required, children }: FieldProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium">
        {label}
        {required && <span className="text-destructive ml-0.5">*</span>}
      </label>
      {children}
      {error && <span className="text-xs text-destructive">{error}</span>}
    </div>
  );
}

// ── File Input component ──────────────────────────────────────────────────────

interface FileInputItem {
  id: string;
  file: File;
  descripcion: string;
}

interface FileInputProps {
  label: string;
  files: FileInputItem[];
  onFilesChange: (files: FileInputItem[]) => void;
  accept?: string;
  error?: string;
  maxFiles?: number;
}

function FileInput({
  label,
  files,
  onFilesChange,
  accept = ".pdf,.doc,.docx,.jpg,.jpeg,.png",
  error,
  maxFiles,
}: FileInputProps) {
  const inputId = `file-${label.replace(/\s+/g, "-").toLowerCase()}`;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files ?? []);
    if (!selected.length) return;
    if (maxFiles && files.length + selected.length > maxFiles) {
      toast.error(
        `Máximo ${maxFiles} archivo${maxFiles !== 1 ? "s" : ""} permitidos`,
      );
      return;
    }
    const newFiles = selected.map((file) => ({
      id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      file,
      descripcion: "",
    }));
    onFilesChange([...files, ...newFiles]);
    e.target.value = "";
  };

  const removeFile = (id: string) => {
    onFilesChange(files.filter((f) => f.id !== id));
  };

  const updateDescripcion = (id: string, descripcion: string) => {
    onFilesChange(files.map((f) => (f.id === id ? { ...f, descripcion } : f)));
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">{label}</span>
        <label
          htmlFor={inputId}
          className="cursor-pointer text-xs text-primary hover:text-primary/80 font-medium"
        >
          + Agregar archivo
        </label>
      </div>

      <input
        id={inputId}
        type="file"
        accept={accept}
        multiple
        className="hidden"
        onChange={handleFileChange}
      />

      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((item) => (
            <div
              key={item.id}
              className="flex items-start gap-2 p-2 bg-muted/50 rounded-lg border"
            >
              <FileText className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium truncate">{item.file.name}</p>
                <p className="text-[10px] text-muted-foreground">
                  {(item.file.size / 1024 / 1024).toFixed(2)} MB
                </p>
                <Input
                  placeholder="Descripción (opcional)"
                  value={item.descripcion}
                  onChange={(e) => updateDescripcion(item.id, e.target.value)}
                  className="mt-1 h-7 text-xs"
                />
              </div>
              <button
                type="button"
                onClick={() => removeFile(item.id)}
                className="text-muted-foreground hover:text-destructive p-1"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </div>
      )}

      {files.length === 0 && (
        <p className="text-xs text-muted-foreground italic py-2">
          No hay archivos agregados
        </p>
      )}

      {error && <span className="text-xs text-destructive">{error}</span>}
    </div>
  );
}

// ── Area row component ────────────────────────────────────────────────────────

interface AreaRowProps {
  area: AreaDistribucionData;
  areas: { id: string; nombre: string }[];
  onChange: (area: AreaDistribucionData) => void;
  onRemove: () => void;
  error?: string;
  allAreas: AreaDistribucionData[];
}

function AreaRow({
  area,
  areas,
  onChange,
  onRemove,
  error,
  allAreas,
}: AreaRowProps) {
  const usedAreaIds = allAreas.filter((a) => a !== area).map((a) => a.area_id);

  const availableAreas = areas.filter((a) => !usedAreaIds.includes(a.id));

  return (
    <div className="flex items-start gap-2 p-3 bg-muted/30 rounded-lg border">
      <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-2">
        <Select
          value={area.area_id}
          onValueChange={(val) => onChange({ ...area, area_id: val })}
        >
          <SelectTrigger className="h-8 text-sm">
            <SelectValue placeholder="Seleccionar área" />
          </SelectTrigger>
          <SelectContent>
            {availableAreas.length === 0 && (
              <SelectItem value="no-areas" disabled>
                {areas.length === 0 ? "Sin áreas disponibles" : "Todas usadas"}
              </SelectItem>
            )}
            {availableAreas.map((a) => (
              <SelectItem key={a.id} value={a.id}>
                {a.nombre}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={area.tipo_participacion}
          onValueChange={(val) =>
            onChange({ ...area, tipo_participacion: val as TipoParticipacion })
          }
        >
          <SelectTrigger className="h-8 text-sm">
            <SelectValue placeholder="Tipo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="PRINCIPAL">Principal</SelectItem>
            <SelectItem value="ADJUNTA">Adjunta</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Button
        type="button"
        variant="ghost"
        size="icon-xs"
        onClick={onRemove}
        className="text-muted-foreground hover:text-destructive shrink-0 mt-0.5"
      >
        <Trash2 className="h-3.5 w-3.5" />
      </Button>

      {error && (
        <span className="text-xs text-destructive col-span-full">{error}</span>
      )}
    </div>
  );
}

// ── Step 1: Tipo de persona ───────────────────────────────────────────────────

interface Step1Props {
  tipoPersona: TipoPersona;
  onChange: (val: TipoPersona) => void;
}

function Step1TipoPersona({ tipoPersona, onChange }: Step1Props) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">
          Tipo de Persona
        </h2>
        <p className="text-sm text-muted-foreground mb-4">
          Seleccione el tipo de persona que realiza el trámite.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {(Object.keys(TIPO_PERSONA) as TipoPersona[]).map((key) => {
          const token = TIPO_PERSONA[key];
          const isSelected = tipoPersona === key;
          return (
            <button
              key={key}
              type="button"
              onClick={() => onChange(key)}
              className={`
                flex flex-col items-start gap-2 p-4 rounded-xl border-2 text-left
                transition-all
                ${
                  isSelected
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-primary/40 bg-card"
                }
              `}
            >
              <div className="flex items-center gap-2">
                <div
                  className={`
                  w-5 h-5 rounded-full border-2 flex items-center justify-center
                  ${isSelected ? "border-primary bg-primary" : "border-muted-foreground"}
                `}
                >
                  {isSelected && (
                    <CheckCircle2 className="h-3 w-3 text-primary-foreground" />
                  )}
                </div>
                <span className="font-medium text-sm">{token.label}</span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ── Step 2: Datos del interesado ─────────────────────────────────────────────

interface Step2Props {
  data: CreateTramiteData["expediente"];
  onChange: (patch: Partial<CreateTramiteData["expediente"]>) => void;
  errors: Record<string, string>;
}

function Step2DatosInteresado({ data, onChange, errors }: Step2Props) {
  const isNatural = data.tipo_persona === "NATURAL";
  const isJuridica = data.tipo_persona === "JURIDICA";
  const isColegiado = data.tipo_persona === "COLEGIADO";

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">
          Datos del Interesado
        </h2>
        <p className="text-sm text-muted-foreground mb-4">
          Complete los datos de la persona que realiza el trámite.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4">
        {/* Identificación según tipo */}
        {isNatural && (
          <Field label="DNI" error={errors.dni} required>
            <Input
              placeholder="12345678"
              value={data.dni ?? ""}
              maxLength={8}
              onChange={(e) => onChange({ dni: e.target.value || null })}
            />
          </Field>
        )}

        {isJuridica && (
          <Field label="RUC" error={errors.ruc} required>
            <Input
              placeholder="12345678901"
              value={data.ruc ?? ""}
              maxLength={11}
              onChange={(e) => onChange({ ruc: e.target.value || null })}
            />
          </Field>
        )}

        {isColegiado && (
          <Field label="CIP" error={errors.cip}>
            <Input
              placeholder="12345"
              value={data.cip ?? ""}
              maxLength={20}
              onChange={(e) => onChange({ cip: e.target.value || null })}
            />
          </Field>
        )}

        {isNatural && (
          <Field label="Nombres" error={errors.nombres} required>
            <Input
              placeholder="Nombres completos"
              value={data.nombres ?? ""}
              maxLength={150}
              onChange={(e) => onChange({ nombres: e.target.value || null })}
            />
          </Field>
        )}

        {isNatural && (
          <Field label="Apellidos" error={errors.apellidos} required>
            <Input
              placeholder="Apellidos completos"
              value={data.apellidos ?? ""}
              maxLength={150}
              onChange={(e) => onChange({ apellidos: e.target.value || null })}
            />
          </Field>
        )}

        {isJuridica && (
          <Field label="Razón Social" error={errors.razon_social} required>
            <Input
              placeholder="Nombre o razón social"
              value={data.razon_social ?? ""}
              maxLength={255}
              onChange={(e) =>
                onChange({ razon_social: e.target.value || null })
              }
            />
          </Field>
        )}

        {(isNatural || isColegiado) && (
          <Field label="Nombres" error={errors.nombres}>
            <Input
              placeholder="Nombres completos"
              value={data.nombres ?? ""}
              maxLength={150}
              onChange={(e) => onChange({ nombres: e.target.value || null })}
            />
          </Field>
        )}

        {(isNatural || isColegiado) && (
          <Field label="Apellidos" error={errors.apellidos}>
            <Input
              placeholder="Apellidos completos"
              value={data.apellidos ?? ""}
              maxLength={150}
              onChange={(e) => onChange({ apellidos: e.target.value || null })}
            />
          </Field>
        )}

        {/* Contacto */}
        <Field label="Correo electrónico" error={errors.correo}>
          <Input
            type="email"
            placeholder="correo@ejemplo.com"
            value={data.correo ?? ""}
            onChange={(e) => onChange({ correo: e.target.value || null })}
          />
        </Field>

        <Field label="Teléfono" error={errors.telefono}>
          <Input
            placeholder="999999999"
            value={data.telefono ?? ""}
            maxLength={20}
            onChange={(e) => onChange({ telefono: e.target.value || null })}
          />
        </Field>
      </div>
    </div>
  );
}

// ── Step 3: Datos del documento ───────────────────────────────────────────────

interface Step3Props {
  data: CreateTramiteData["expediente"];
  onChange: (patch: Partial<CreateTramiteData["expediente"]>) => void;
  errors: Record<string, string>;
  control: ReturnType<typeof useForm<CreateTramiteData>>["control"];
  register: ReturnType<typeof useForm<CreateTramiteData>>["register"];
}

function Step3DatosDocumento({ data, onChange, errors, control, register }: Step3Props) {
  const id = useId();
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">
          Datos del Documento
        </h2>
        <p className="text-sm text-muted-foreground mb-4">
          Complete la información del documento que presenta.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4">
        <Field label="Tipo de documento" error={errors.tipo_documento} required>
          <InputSelectTipoDocumento
            field={{ name: "expediente.tipo_documento_id", label: "Tipo de documento", type: "select-tipo-documento" }}
            control={control as any}
            register={register as any}
            id={id}
            error={errors.tipo_documento ? { message: errors.tipo_documento } : undefined}
          />
        </Field>

        <Field label="Número de documento" error={errors.numero_documento}>
          <Input
            placeholder="Número del documento"
            value={data.numero_documento ?? ""}
            maxLength={50}
            onChange={(e) =>
              onChange({ numero_documento: e.target.value || null })
            }
          />
        </Field>

        <Field label="Número de folios" error={errors.numero_folios}>
          <Input
            type="number"
            min={0}
            placeholder="0"
            value={data.numero_folios}
            onChange={(e) =>
              onChange({ numero_folios: parseInt(e.target.value) || 0 })
            }
          />
        </Field>

        <div className="sm:col-span-2">
          <Field label="Asunto" error={errors.asunto} required>
            <Input
              placeholder="Asunto del documento"
              value={data.asunto}
              onChange={(e) => onChange({ asunto: e.target.value })}
            />
          </Field>
        </div>

        <div className="sm:col-span-2">
          <Field label="Observaciones" error={errors.observaciones}>
            <Textarea
              placeholder="Observaciones adicionales (opcional)"
              value={data.observaciones ?? ""}
              onChange={(e) =>
                onChange({ observaciones: e.target.value || null })
              }
              className="min-h-20"
            />
          </Field>
        </div>
      </div>
    </div>
  );
}

// ── Step 4: Archivos ──────────────────────────────────────────────────────────

interface Step4Props {
  data: CreateTramiteData["expediente"]["archivos"];
  onChange: (
    patch: Partial<CreateTramiteData["expediente"]["archivos"]>,
  ) => void;
  principalError?: string;
}

function Step4Archivos({ data, onChange, principalError }: Step4Props) {
  const handlePrincipalChange = (files: FileInputItem[]) => {
    // Only one principal allowed — take first
    const principalFiles = files.slice(0, 1).map((item) => ({
      tipo_archivo: "PRINCIPAL" as const,
      nombre_original: item.file.name,
      descripcion: item.descripcion,
      archivo: item.file,
    }));
    onChange({ principal: principalFiles });
  };

  const handleAnexosChange = (files: FileInputItem[]) => {
    const anexoFiles = files.map((item) => ({
      tipo_archivo: "ANEXO" as const,
      nombre_original: item.file.name,
      descripcion: item.descripcion,
      archivo: item.file,
    }));
    onChange({ anexo: anexoFiles });
  };

  const principalItems: FileInputItem[] = data.principal.map((f) => ({
    id: f.nombre_original,
    file: f.archivo as File,
    descripcion: f.descripcion ?? "",
  }));

  const anexoItems: FileInputItem[] = data.anexo.map((f) => ({
    id: f.nombre_original,
    file: f.archivo as File,
    descripcion: f.descripcion ?? "",
  }));

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">
          Archivos
        </h2>
        <p className="text-sm text-muted-foreground mb-4">
          Agregue el documento principal y archivos anexos.
        </p>
      </div>

      <div className="space-y-6">
        <div className="p-4 border-2 border-dashed rounded-xl border-primary/30 bg-primary/5">
          <FileInput
            label="Documento principal (obligatorio)"
            files={principalItems}
            onFilesChange={handlePrincipalChange}
            accept=".pdf,.doc,.docx"
            maxFiles={1}
            error={principalError}
          />
          {principalItems.length === 0 && (
            <p className="text-xs text-muted-foreground mt-2">
              Debe adjuntar exactamente un archivo principal
            </p>
          )}
        </div>

        <FileInput
          label="Anexos (opcional)"
          files={anexoItems}
          onFilesChange={handleAnexosChange}
          accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
          error={undefined}
        />
      </div>
    </div>
  );
}

// ── Step 5: Prioridad ─────────────────────────────────────────────────────────

interface Step5Props {
  prioridad: PrioridadSolicitud;
  observacion: string | null;
  onPrioridadChange: (val: PrioridadSolicitud) => void;
  onObservacionChange: (val: string | null) => void;
}

function Step5Prioridad({
  prioridad,
  observacion,
  onPrioridadChange,
  onObservacionChange,
}: Step5Props) {
  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">
          Prioridad y Observación
        </h2>
        <p className="text-sm text-muted-foreground mb-4">
          Asigne la prioridad de atención y una observación general.
        </p>
      </div>

      <div className="space-y-4">
        <Field label="Prioridad de atención">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {(Object.keys(PRIORIDAD_SOLICITUD) as PrioridadSolicitud[]).map(
              (key) => {
                const token = PRIORIDAD_SOLICITUD[key];
                const isSelected = prioridad === key;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => onPrioridadChange(key)}
                    className={`
                    flex flex-col items-center gap-1.5 p-3 rounded-xl border-2 text-center
                    transition-all
                    ${
                      isSelected
                        ? "border-primary bg-primary/5"
                        : "border-border hover:border-primary/40 bg-card"
                    }
                  `}
                  >
                    <span className="text-sm font-medium">{token.label}</span>
                  </button>
                );
              },
            )}
          </div>
        </Field>

        <Field label="Observación general">
          <Textarea
            placeholder="Contexto general de la solicitud (opcional)"
            value={observacion ?? ""}
            onChange={(e) => onObservacionChange(e.target.value || null)}
            className="min-h-24"
          />
        </Field>
      </div>
    </div>
  );
}

// ── Step 6: Distribución de áreas ─────────────────────────────────────────────

interface Step6Props {
  areas: AreaDistribucionData[];
  onChange: (areas: AreaDistribucionData[]) => void;
  error?: string;
}

function Step6Areas({ areas, onChange, error }: Step6Props) {
  const addArea = () => {
    const newArea: AreaDistribucionData = {
      area_id: "",
      tipo_participacion: "PRINCIPAL",
      observacion: null,
    };
    onChange([...areas, newArea]);
  };

  const updateArea = (index: number, patch: Partial<AreaDistribucionData>) => {
    const updated = areas.map((a, i) => (i === index ? { ...a, ...patch } : a));
    onChange(updated);
  };

  const removeArea = (index: number) => {
    onChange(areas.filter((_, i) => i !== index));
  };

  const principalsCount = areas.filter(
    (a) => a.tipo_participacion === "PRINCIPAL",
  ).length;
  const adjuntasCount = areas.filter(
    (a) => a.tipo_participacion === "ADJUNTA",
  ).length;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">
          Distribución de Áreas
        </h2>
        <p className="text-sm text-muted-foreground mb-4">
          Asigne una o más áreas al trámite indicando su tipo de participación.
        </p>

        {/* TODO marker */}
        <div className="flex items-center gap-2 p-3 mb-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <AlertTriangle className="h-4 w-4 text-yellow-600 dark:text-yellow-500 shrink-0" />
          <p className="text-xs text-yellow-700 dark:text-yellow-400">
            <strong>TODO:</strong> El catálogo de áreas se reemplazará con la
            chamada real a{" "}
            <code className="bg-yellow-100 dark:bg-yellow-900/50 px-1 rounded">
              GET /api/areas
            </code>{" "}
            cuando el endpoint exista. Áreas actuales son placeholders.
          </p>
        </div>

        {/* Summary */}
        {areas.length > 0 && (
          <div className="flex gap-3 mb-4">
            <Badge
              variant="outline"
              className="bg-primary/10 text-primary border-primary/20"
            >
              {principalsCount} principal{principalsCount !== 1 ? "es" : ""}
            </Badge>
            <Badge
              variant="outline"
              className="bg-secondary/50 text-secondary-foreground border-secondary"
            >
              {adjuntasCount} adjunta{adjuntasCount !== 1 ? "s" : ""}
            </Badge>
          </div>
        )}
      </div>

      {/* Area list */}
      <div className="space-y-2">
        {areas.map((area, idx) => (
          <AreaRow
            key={idx}
            area={area}
            areas={PLACEHOLDER_AREAS.map((a) => ({
              id: a.id,
              nombre: a.nombre,
            }))}
            onChange={(updated) => updateArea(idx, updated)}
            onRemove={() => removeArea(idx)}
            allAreas={areas}
            error={undefined}
          />
        ))}
      </div>

      {areas.length === 0 && (
        <p className="text-sm text-muted-foreground italic py-4 text-center">
          No hay áreas agregadas. Haga clic en &quot;Agregar área&quot; para
          asignar al menos una.
        </p>
      )}

      <Button
        type="button"
        variant="outline"
        className="gap-2"
        onClick={addArea}
      >
        <Plus className="h-4 w-4" />
        Agregar área
      </Button>

      {error && <span className="text-xs text-destructive">{error}</span>}
    </div>
  );
}

// ── Step 7: Revisión ─────────────────────────────────────────────────────────

interface Step7Props {
  data: CreateTramiteData;
}

function Step7Revision({ data }: Step7Props) {
  const { expediente, prioridad, observacion, areas_distribucion } = data;
  const { tiposDocumento } = useTiposDocumento();

  const tipoPersonaLabel = TIPO_PERSONA[expediente.tipo_persona]?.label;
  const prioridadLabel = PRIORIDAD_SOLICITUD[prioridad]?.label;

  const principals = areas_distribucion.filter(
    (a) => a.tipo_participacion === "PRINCIPAL",
  );
  const adjuntas = areas_distribucion.filter(
    (a) => a.tipo_participacion === "ADJUNTA",
  );

  // Resolve area names from placeholders
  const getAreaName = (areaId: string) => {
    const found = PLACEHOLDER_AREAS.find((a) => a.id === areaId);
    return found?.nombre ?? areaId;
  };

  const getInteresadoLabel = () => {
    if (expediente.tipo_persona === "NATURAL") {
      return [expediente.nombres, expediente.apellidos]
        .filter(Boolean)
        .join(" ");
    }
    if (expediente.tipo_persona === "JURIDICA") {
      return expediente.razon_social ?? "—";
    }
    return [expediente.nombres, expediente.apellidos].filter(Boolean).join(" ");
  };

  const getIdentificacionLabel = () => {
    if (expediente.tipo_persona === "NATURAL") return expediente.dni ?? "—";
    if (expediente.tipo_persona === "JURIDICA") return expediente.ruc ?? "—";
    return expediente.cip ?? "—";
  };

  const getTipoDocumentoLabel = () => {
    if (!expediente.tipo_documento_id) return "—";
    const found = tiposDocumento.find((t) => t.id === expediente.tipo_documento_id);
    return found ? `${found.nombre}${found.descripcion ? ` — ${found.descripcion}` : ""}` : expediente.tipo_documento_id;
  };

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground mb-3">
          Revisión Final
        </h2>
        <p className="text-sm text-muted-foreground mb-4">
          Verifique todos los datos antes de enviar el trámite.
        </p>
      </div>

      <div className="space-y-4">
        {/* Interesado */}
        <div className="app-card p-4 space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Interesado
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-muted-foreground">Tipo: </span>
              <span className="font-medium">{tipoPersonaLabel}</span>
            </div>
            <div>
              <span className="text-muted-foreground">ID: </span>
              <span className="font-mono">{getIdentificacionLabel()}</span>
            </div>
            <div className="sm:col-span-2">
              <span className="text-muted-foreground">Nombre: </span>
              <span className="font-medium">{getInteresadoLabel()}</span>
            </div>
            {expediente.correo && (
              <div>
                <span className="text-muted-foreground">Correo: </span>
                <span>{expediente.correo}</span>
              </div>
            )}
            {expediente.telefono && (
              <div>
                <span className="text-muted-foreground">Teléfono: </span>
                <span>{expediente.telefono}</span>
              </div>
            )}
          </div>
        </div>

        {/* Documento */}
        <div className="app-card p-4 space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Documento
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-muted-foreground">Tipo: </span>
              <span className="font-medium">{getTipoDocumentoLabel()}</span>
            </div>
            {expediente.numero_documento && (
              <div>
                <span className="text-muted-foreground">Número: </span>
                <span className="font-mono">{expediente.numero_documento}</span>
              </div>
            )}
            <div>
              <span className="text-muted-foreground">Folios: </span>
              <span>{expediente.numero_folios}</span>
            </div>
            <div className="sm:col-span-2">
              <span className="text-muted-foreground">Asunto: </span>
              <span className="font-medium">{expediente.asunto}</span>
            </div>
            {expediente.observaciones && (
              <div className="sm:col-span-2">
                <span className="text-muted-foreground">Obs: </span>
                <span className="text-muted-foreground italic">
                  {expediente.observaciones}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Archivos */}
        <div className="app-card p-4 space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Archivos
          </h3>
          {expediente.archivos.principal.length > 0 ? (
            <div className="space-y-1">
              {expediente.archivos.principal.map((f) => (
                <div
                  key={f.nombre_original}
                  className="flex items-center gap-2 text-sm"
                >
                  <FileText className="h-4 w-4 text-primary shrink-0" />
                  <span className="font-medium">{f.nombre_original}</span>
                  <Badge className="bg-primary/10 text-primary border-primary/20 text-[10px]">
                    Principal
                  </Badge>
                </div>
              ))}
              {expediente.archivos.anexo.map((f) => (
                <div
                  key={f.nombre_original}
                  className="flex items-center gap-2 text-sm"
                >
                  <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span>{f.nombre_original}</span>
                  <Badge variant="outline" className="text-[10px]">
                    Anexo
                  </Badge>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground italic">Sin archivos</p>
          )}
          {expediente.archivos.anexo.length === 0 && (
            <p className="text-xs text-muted-foreground">
              {expediente.archivos.principal.length} principal(es)
            </p>
          )}
        </div>

        {/* Prioridad */}
        <div className="app-card p-4 space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Solicitud
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm">
            <div>
              <span className="text-muted-foreground">Prioridad: </span>
              <Badge className={PRIORIDAD_SOLICITUD[prioridad].badgeClass}>
                {prioridadLabel}
              </Badge>
            </div>
            {observacion && (
              <div className="sm:col-span-2">
                <span className="text-muted-foreground">Observación: </span>
                <span className="italic">{observacion}</span>
              </div>
            )}
          </div>
        </div>

        {/* Áreas */}
        <div className="app-card p-4 space-y-2">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
            Distribución de Áreas
          </h3>
          {areas_distribucion.length > 0 ? (
            <div className="space-y-2">
              {principals.length > 0 && (
                <div>
                  <span className="text-xs text-muted-foreground uppercase">
                    Principales
                  </span>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {principals.map((a) => (
                      <Badge
                        key={a.area_id}
                        className="bg-primary/10 text-primary border-primary/20"
                      >
                        {getAreaName(a.area_id)}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {adjuntas.length > 0 && (
                <div>
                  <span className="text-xs text-muted-foreground uppercase">
                    Adjuntas
                  </span>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {adjuntas.map((a) => (
                      <Badge key={a.area_id} variant="outline">
                        {getAreaName(a.area_id)}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground italic">
              Sin áreas asignadas
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function CrearTramitePage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitSuccess, setSubmitSuccess] = useState<string | null>(null);

  const { mutate: crearTramite, isPending: isSubmitting } = useCrearTramite();

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    trigger,
    control,
    formState: { errors },
  } = useForm<CreateTramiteData>({
    resolver: zodResolver(CreateTramiteSchema),
    defaultValues,
    mode: "onBlur",
  });

  const formValues = watch();

  // Extract flat errors for display
  const flatErrors: Record<string, string> = {};
  for (const [key, err] of Object.entries(errors)) {
    if (err?.message) {
      flatErrors[key] = err.message;
    }
  }

  const goToStep = (step: number) => {
    if (step < currentStep) {
      setCurrentStep(step);
    }
  };

  const nextStep = async () => {
    // Validate current step fields before advancing
    let isValid = true;

    if (currentStep === 1) {
      // Step 1: tipo_persona is always valid (has default)
      isValid = true;
    } else if (currentStep === 2) {
      // Step 2: validate fields based on tipo_persona
      isValid = await trigger([
        "expediente.tipo_persona",
        "expediente.dni",
        "expediente.ruc",
        "expediente.cip",
        "expediente.razon_social",
        "expediente.nombres",
        "expediente.apellidos",
      ]);
    } else if (currentStep === 3) {
      isValid = await trigger([
        "expediente.tipo_documento_id",
        "expediente.asunto",
        "expediente.numero_folios",
      ]);
    } else if (currentStep === 4) {
      // Step 4: must have exactly one principal
      if (formValues.expediente.archivos.principal.length === 0) {
        toast.error("Debe agregar al menos un archivo principal");
        isValid = false;
      }
    } else if (currentStep === 5) {
      isValid = await trigger(["prioridad"]);
    } else if (currentStep === 6) {
      // Step 6: at least one area required
      if (formValues.areas_distribucion.length === 0) {
        toast.error("Debe agregar al menos un área");
        isValid = false;
      } else {
        // Also check each area has an area_id selected
        const allHaveArea = formValues.areas_distribucion.every(
          (a) => a.area_id !== "",
        );
        if (!allHaveArea) {
          toast.error("Todas las áreas deben tener un área seleccionada");
          isValid = false;
        }
      }
    }

    if (!isValid) return;

    setCompletedSteps((prev) =>
      prev.includes(currentStep) ? prev : [...prev, currentStep],
    );
    setCurrentStep((s) => Math.min(s + 1, TOTAL_STEPS));
  };

  const prevStep = () => {
    setCurrentStep((s) => Math.max(s - 1, 1));
  };

  const onSubmit = (data: CreateTramiteData) => {
    setSubmitError(null);
    setSubmitSuccess(null);

    crearTramite(data, {
      onSuccess: (result) => {
        // Unwrap from ApiResponse envelope - result is SolicitudDetail
        const created = result as { id?: string } & { data?: { id?: string } };
        const id = created.data?.id ?? created.id;

        setSubmitSuccess(
          id
            ? `Trámite creado exitosamente. ID: ${id}`
            : "Trámite creado exitosamente.",
        );

        toast.success("Trámite creado correctamente");

        // Redirect after a brief delay to show success message
        setTimeout(() => {
          router.push("/solicitudes");
        }, 1500);
      },
      onError: (err) => {
        const message =
          err instanceof Error
            ? err.message
            : "No se pudo crear el trámite. Verifique los datos.";
        setSubmitError(message);
        toast.error(message);
      },
    });
  };

  const handleStepClick = (step: number) => {
    if (completedSteps.includes(step) || step === 1) {
      goToStep(step);
    }
  };

  return (
    <PageWrapper
      title="Nueva Solicitud"
      description="Cree un nuevo trámite de Mesa de Partes"
      icon={<FileText className="h-6 w-6 text-primary" />}
    >
      {/* Stepper */}
      <div className="app-card p-4">
        <Stepper
          currentStep={currentStep}
          labels={STEP_LABELS}
          onStepClick={handleStepClick}
          completedSteps={completedSteps}
        />
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* Step content */}
        <div className="app-card p-4 sm:p-6">
          {currentStep === 1 && (
            <Step1TipoPersona
              tipoPersona={formValues.expediente.tipo_persona}
              onChange={(val) =>
                setValue("expediente.tipo_persona", val, {
                  shouldValidate: true,
                })
              }
            />
          )}

          {currentStep === 2 && (
            <Step2DatosInteresado
              data={formValues.expediente}
              onChange={(patch) =>
                setValue(
                  "expediente",
                  { ...formValues.expediente, ...patch },
                  {
                    shouldValidate: true,
                  },
                )
              }
              errors={flatErrors}
            />
          )}

          {currentStep === 3 && (
            <Step3DatosDocumento
              data={formValues.expediente}
              onChange={(patch) =>
                setValue(
                  "expediente",
                  { ...formValues.expediente, ...patch },
                  {
                    shouldValidate: true,
                  },
                )
              }
              errors={flatErrors}
              control={control}
              register={register}
            />
          )}

          {currentStep === 4 && (
            <Step4Archivos
              data={formValues.expediente.archivos}
              onChange={(patch) =>
                setValue(
                  "expediente.archivos",
                  { ...formValues.expediente.archivos, ...patch },
                  { shouldValidate: true },
                )
              }
              principalError={flatErrors["expediente.archivos"]}
            />
          )}

          {currentStep === 5 && (
            <Step5Prioridad
              prioridad={formValues.prioridad}
              observacion={formValues.observacion}
              onPrioridadChange={(val) =>
                setValue("prioridad", val, { shouldValidate: true })
              }
              onObservacionChange={(val) => setValue("observacion", val)}
            />
          )}

          {currentStep === 6 && (
            <Step6Areas
              areas={formValues.areas_distribucion}
              onChange={(areas) =>
                setValue("areas_distribucion", areas, { shouldValidate: true })
              }
              error={flatErrors.areas_distribucion}
            />
          )}

          {currentStep === 7 && <Step7Revision data={formValues} />}
        </div>

        {/* Success/Error messages */}
        {submitSuccess && (
          <div className="success-card p-4">
            <div className="flex items-center gap-2 success-text">
              <CheckCircle2 className="h-5 w-5" />
              <span className="font-medium">{submitSuccess}</span>
            </div>
          </div>
        )}

        {submitError && (
          <div className="app-card p-4 border-destructive/30 bg-destructive/5">
            <div className="flex items-center gap-2 text-destructive">
              <AlertTriangle className="h-5 w-5" />
              <span className="font-medium">{submitError}</span>
            </div>
          </div>
        )}

        {/* Navigation buttons */}
        <div className="flex items-center justify-between gap-3">
          <Button
            type="button"
            variant="outline"
            className="gap-2"
            onClick={prevStep}
            disabled={currentStep === 1 || isSubmitting}
          >
            <ArrowLeft className="h-4 w-4" />
            Anterior
          </Button>

          <div className="flex items-center gap-2">
            {currentStep < TOTAL_STEPS ? (
              <Button type="button" className="gap-2" onClick={nextStep}>
                Siguiente
                <ArrowRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button
                type="submit"
                className="gap-2"
                disabled={isSubmitting || !!submitSuccess}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Creando...
                  </>
                ) : (
                  <>
                    <Send className="h-4 w-4" />
                    Enviar trámite
                  </>
                )}
              </Button>
            )}
          </div>
        </div>
      </form>
    </PageWrapper>
  );
}
