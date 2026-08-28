"use client";

/**
 * Libro de Reclamaciones — mock frontend page.
 * Route: /libro-reclamaciones
 *
 * Reference: https://servicioscdl.ciplima.org.pe/libro-de-reclamaciones/
 *
 * HARD CONSTRAINT: FRONTEND ONLY. No backend endpoint, service calls, API hooks,
 * database, schema, or migrations. Submit is mock/local only — shows success toast
 * and does not POST anywhere.
 */
import { useCallback, useId, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import {
  BookOpen,
  Building2,
  CheckCircle2,
  FileText,
  Send,
  ShieldCheck,
  User,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import { PageWrapper } from "@/components-app/page/PageWrapper";
import { notify } from "@/errors";

// ── Field name constants ────────────────────────────────────────────────────────

const TIPO_DOCUMENTO_OPTIONS = [
  { label: "DNI", value: "DNI" },
  { label: "CE (Carné de Extranjería)", value: "CE" },
] as const;

const TIPO_BIEN_OPTIONS = [
  { label: "Producto", value: "PRODUCTO" },
  { label: "Servicio", value: "SERVICIO" },
] as const;

const TIPO_RECLAMACION_OPTIONS = [
  { label: "Reclamo", value: "RECLAMO" },
  { label: "Queja", value: "QUEJA" },
] as const;

// ── Zod Schema ────────────────────────────────────────────────────────────────

const LibroReclamacionesSchema = z.object({
  // Block 1: Identificación del consumidor reclamante
  nombre_completo: z
    .string()
    .min(1, "El nombre completo es requerido")
    .max(200, "Máximo 200 caracteres"),
  domicilio: z
    .string()
    .min(1, "El domicilio es requerido")
    .max(300, "Máximo 300 caracteres"),
  tipo_documento: z.enum(["DNI", "CE"], {
    message: "Selecciona un tipo de documento",
  }),
  numero_documento: z
    .string()
    .min(8, "El número de documento debe tener al menos 8 dígitos")
    .max(15, "Máximo 15 caracteres"),
  capitulo: z.string().max(50).nullable().optional(),
  cip: z.string().max(10, "Máximo 10 caracteres").nullable().optional(),
  telefono: z
    .string()
    .min(6, "Mínimo 6 dígitos")
    .max(15, "Máximo 15 caracteres")
    .nullable()
    .optional(),
  email: z
    .string()
    .email("Ingresa un correo electrónico válido")
    .max(255, "Máximo 255 caracteres")
    .nullable()
    .optional(),
  padre_madre: z.string().max(200).nullable().optional(),

  // Block 2: Identificación del bien contratado
  tipo_bien: z.enum(["PRODUCTO", "SERVICIO"], {
    message: "Selecciona el tipo de bien contratado",
  }),
  descripcion_bien: z
    .string()
    .min(1, "La descripción es requerida")
    .max(500, "Máximo 500 caracteres"),

  // Block 3: Detalle de la reclamación
  tipo_reclamacion: z.enum(["RECLAMO", "QUEJA"], {
    message: "Selecciona el tipo de reclamación",
  }),
  area_oficina: z
    .string()
    .min(1, "El área u oficina es requerida")
    .max(200, "Máximo 200 caracteres"),
  descripcion_detalle: z
    .string()
    .min(10, "La descripción debe tener al menos 10 caracteres")
    .max(2000, "Máximo 2000 caracteres"),
  pedido_accion: z.string().max(1000, "Máximo 1000 caracteres").nullable().optional(),
});

type LibroReclamacionesFormData = z.infer<typeof LibroReclamacionesSchema>;

// ── Defaults ──────────────────────────────────────────────────────────────────

const FORM_DEFAULTS: Partial<LibroReclamacionesFormData> = {
  tipo_documento: "DNI",
  tipo_bien: "SERVICIO",
  tipo_reclamacion: "RECLAMO",
  capitulo: null,
  cip: null,
  telefono: null,
  email: null,
  padre_madre: null,
  pedido_accion: null,
};

// ── Section Card wrapper ───────────────────────────────────────────────────────

interface SectionCardProps {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
}

function SectionCard({ title, icon: Icon, children }: SectionCardProps) {
  return (
    <div className="rounded-xl border border-border/50 bg-card p-4 space-y-4">
      <div className="flex items-center gap-2 border-b border-border/40 pb-2">
        <Icon className="h-4 w-4 text-primary" />
        <h3 className="text-sm font-semibold uppercase tracking-wide">{title}</h3>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">{children}</div>
    </div>
  );
}

// ── Field wrapper ─────────────────────────────────────────────────────────────

interface FieldProps {
  label: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
  className?: string;
  fullWidth?: boolean;
}

function Field({
  label,
  required,
  error,
  children,
  className = "",
  fullWidth = false,
}: FieldProps) {
  return (
    <div
      className={`
        flex flex-col gap-1.5
        ${fullWidth ? "md:col-span-2" : ""}
        ${className}
      `}
    >
      <Label htmlFor={label} className="text-sm font-medium">
        {label}
        {required && <span className="text-destructive ml-0.5">*</span>}
      </Label>
      {children}
      {error && (
        <p className="text-xs text-destructive">{error}</p>
      )}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────

export default function LibroReclamacionesPage() {
  const formId = useId();
  const [isSubmitted, setIsSubmitted] = useState(false);

  const formMethods = useForm<LibroReclamacionesFormData>({
    resolver: zodResolver(LibroReclamacionesSchema),
    defaultValues: FORM_DEFAULTS,
    mode: "onBlur",
  });

  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    watch,
  } = formMethods;

  const tipoReclamacion = watch("tipo_reclamacion");

  const onSubmit = useCallback(
    async (_data: LibroReclamacionesFormData) => {
      // Simulated network latency for realistic UX
      await new Promise((resolve) => setTimeout(resolve, 800));
      setIsSubmitted(true);
      notify.success("Reclamación registrada correctamente");
    },
    []
  );

  if (isSubmitted) {
    return (
      <PageWrapper
        title="Libro de Reclamaciones"
        description="Registro de reclamaciones y quejas"
        icon={<BookOpen className="h-6 w-6 text-primary" />}
      >
        <div className="flex flex-col items-center justify-center py-16 gap-6 text-center">
          <div className="p-4 rounded-full bg-green-100 dark:bg-green-900/30">
            <CheckCircle2 className="h-12 w-12 text-green-600 dark:text-green-400" />
          </div>
          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-foreground">
              Reclamación registrada
            </h2>
            <p className="text-muted-foreground max-w-md">
              Su reclamación ha sido registrada exitosamente. Puede generar una constancia
              de registro usando el botón abaixo.
            </p>
          </div>
          <div className="flex gap-3">
            <Button
              variant="outline"
              onClick={() => {
                setIsSubmitted(false);
                formMethods.reset(FORM_DEFAULTS);
              }}
            >
              Nueva reclamación
            </Button>
          </div>
        </div>

        {/* Constancia de registro */}
        <div className="mt-8 rounded-xl border border-border/50 bg-card p-4">
          <div className="flex items-center gap-2 border-b border-border/40 pb-2 mb-4">
            <ShieldCheck className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold uppercase tracking-wide">
              Constancia de registro
            </h3>
          </div>
          <div className="space-y-3 text-sm">
            <p className="text-muted-foreground">
              Su reclamación ha sido recibida y registrada en nuestros sistemas.
            </p>
            <div className="rounded-lg bg-muted/50 p-3 font-mono text-xs">
              <p><strong>Código de seguimiento:</strong> LR-{Date.now().toString(36).toUpperCase()}</p>
              <p><strong>Fecha:</strong> {new Date().toLocaleDateString("es-PE")}</p>
              <p><strong>Estado:</strong> Registrado</p>
            </div>
          </div>
        </div>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper
      title="Libro de Reclamaciones"
      description="Formulario de reclamaciones y quejas — Ley N° 29571"
      icon={<BookOpen className="h-6 w-6 text-primary" />}
    >
      <form
        id={formId}
        onSubmit={(e) => {
          e.preventDefault();
          void handleSubmit(onSubmit)(e);
        }}
        className="space-y-6"
        noValidate
      >
        {/* ── Block 1: Identificación del consumidor reclamante ────────────── */}
        <SectionCard title="Identificación del consumidor reclamante" icon={User}>
          <Field
            label="Nombre completo"
            required
            error={errors.nombre_completo?.message}
            fullWidth
          >
            <Input
              id="nombre_completo"
              placeholder="Ej: Juan Pérez García"
              {...register("nombre_completo")}
              aria-invalid={!!errors.nombre_completo}
            />
          </Field>

          <Field
            label="Domicilio"
            required
            error={errors.domicilio?.message}
            fullWidth
          >
            <Input
              id="domicilio"
              placeholder="Ej: Av. Arequipa 1234, Lima"
              {...register("domicilio")}
              aria-invalid={!!errors.domicilio}
            />
          </Field>

          <Field label="Tipo de documento" required error={errors.tipo_documento?.message}>
            <Select
              onValueChange={(val) =>
                formMethods.setValue("tipo_documento", val as "DNI" | "CE", {
                  shouldValidate: true,
                })
              }
              defaultValue={FORM_DEFAULTS.tipo_documento}
            >
              <SelectTrigger id="tipo_documento" aria-invalid={!!errors.tipo_documento}>
                <SelectValue placeholder="Seleccione..." />
              </SelectTrigger>
              <SelectContent>
                {TIPO_DOCUMENTO_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <Field
            label="Número de documento"
            required
            error={errors.numero_documento?.message}
          >
            <Input
              id="numero_documento"
              placeholder="Ej: 12345678"
              {...register("numero_documento")}
              aria-invalid={!!errors.numero_documento}
            />
          </Field>

          <Field label="Capítulo" error={errors.capitulo?.message}>
            <Input
              id="capitulo"
              placeholder="Ej: I"
              {...register("capitulo")}
              aria-invalid={!!errors.capitulo}
            />
          </Field>

          <Field label="CIP N°" error={errors.cip?.message}>
            <Input
              id="cip"
              placeholder="Ej: 12345"
              {...register("cip")}
              aria-invalid={!!errors.cip}
            />
          </Field>

          <Field label="Teléfono" error={errors.telefono?.message}>
            <Input
              id="telefono"
              type="tel"
              placeholder="Ej: 999 888 777"
              {...register("telefono")}
              aria-invalid={!!errors.telefono}
            />
          </Field>

          <Field label="E-mail" error={errors.email?.message}>
            <Input
              id="email"
              type="email"
              placeholder="correo@ejemplo.com"
              {...register("email")}
              aria-invalid={!!errors.email}
            />
          </Field>

          <Field
            label="Padre o Madre (en caso de menor)"
            error={errors.padre_madre?.message}
            fullWidth
          >
            <Input
              id="padre_madre"
              placeholder="Nombre del padre o madre"
              {...register("padre_madre")}
              aria-invalid={!!errors.padre_madre}
            />
          </Field>
        </SectionCard>

        {/* ── Block 2: Identificación del bien contratado ──────────────────── */}
        <SectionCard title="Identificación del bien contratado" icon={Building2}>
          <Field
            label="Tipo de bien"
            required
            error={errors.tipo_bien?.message}
          >
            <Select
              onValueChange={(val) =>
                formMethods.setValue("tipo_bien", val as "PRODUCTO" | "SERVICIO", {
                  shouldValidate: true,
                })
              }
              defaultValue={FORM_DEFAULTS.tipo_bien}
            >
              <SelectTrigger id="tipo_bien" aria-invalid={!!errors.tipo_bien}>
                <SelectValue placeholder="Seleccione..." />
              </SelectTrigger>
              <SelectContent>
                {TIPO_BIEN_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>

          <Field
            label="Descripción del bien / servicio"
            required
            error={errors.descripcion_bien?.message}
            fullWidth
          >
            <Input
              id="descripcion_bien"
              placeholder="Ej: Servicio de consultoría técnica"
              {...register("descripcion_bien")}
              aria-invalid={!!errors.descripcion_bien}
            />
          </Field>
        </SectionCard>

        {/* ── Block 3: Detalle de la reclamación ───────────────────────────── */}
        <SectionCard title="Detalle de la reclamación" icon={FileText}>
          <div className="md:col-span-2 space-y-3">
            <Label className="text-sm font-medium">
              Tipo de reclamación <span className="text-destructive ml-0.5">*</span>
            </Label>
            <RadioGroup
              className="flex gap-6"
              defaultValue={FORM_DEFAULTS.tipo_reclamacion}
              onValueChange={(val) =>
                formMethods.setValue(
                  "tipo_reclamacion",
                  val as "RECLAMO" | "QUEJA",
                  { shouldValidate: true }
                )
              }
            >
              {TIPO_RECLAMACION_OPTIONS.map((opt) => (
                <div key={opt.value} className="flex items-center gap-2">
                  <RadioGroupItem value={opt.value} id={`tipo_${opt.value}`} />
                  <Label htmlFor={`tipo_${opt.value}`} className="font-normal cursor-pointer">
                    {opt.label}
                  </Label>
                </div>
              ))}
            </RadioGroup>
            {errors.tipo_reclamacion && (
              <p className="text-xs text-destructive">
                {errors.tipo_reclamacion.message}
              </p>
            )}

            {/* Help text for claim types */}
            <div className="rounded-lg border border-primary/20 bg-primary/5 p-3 text-xs text-muted-foreground space-y-1">
              <p>
                <strong>Reclamo:</strong> Disconformidad relacionada a productos o
                servicios.
              </p>
              <p>
                <strong>Queja:</strong> Disconformidad no relacionada a
                productos/servicios o malestar por la atención recibida.
              </p>
            </div>
          </div>

          <Field
            label="Área u oficina"
            required
            error={errors.area_oficina?.message}
            fullWidth
          >
            <Input
              id="area_oficina"
              placeholder="Ej: Área de Atención al Cliente"
              {...register("area_oficina")}
              aria-invalid={!!errors.area_oficina}
            />
          </Field>

          <Field
            label="Descripción / detalle"
            required
            error={errors.descripcion_detalle?.message}
            fullWidth
          >
            <Textarea
              id="descripcion_detalle"
              placeholder="Describa el motivo de su reclamación o queja..."
              rows={4}
              {...register("descripcion_detalle")}
              aria-invalid={!!errors.descripcion_detalle}
            />
          </Field>

          {tipoReclamacion === "RECLAMO" && (
            <Field
              label="Pedido del consumidor / acción solicitada"
              error={errors.pedido_accion?.message}
              fullWidth
            >
              <Textarea
                id="pedido_accion"
                placeholder="Indique la acción que solicita para resolver su reclamo..."
                rows={3}
                {...register("pedido_accion")}
                aria-invalid={!!errors.pedido_accion}
              />
            </Field>
          )}
        </SectionCard>

        {/* ── Submit ─────────────────────────────────────────────────────── */}
        <div className="flex justify-end gap-3 pt-2">
          <Button
            type="submit"
            size="lg"
            className="gap-2 font-bold"
            disabled={!isValid}
          >
            <Send className="h-4 w-4" />
            Enviar reclamación
          </Button>
        </div>
      </form>
    </PageWrapper>
  );
}
