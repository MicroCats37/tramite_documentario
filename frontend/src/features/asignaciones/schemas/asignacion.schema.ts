import { z } from "zod";

// ── Legacy Asignacion Schemas ─────────────────────────────────────────────────

/**
 * Asignacion form schema for creating/updating asignaciones.
 */
export const CreateAsignacionSchema = z.object({
  tramite_id: z.string().uuid("ID de trámite inválido"),
  usuario_id: z.string().uuid("ID de usuario inválido"),
  rol: z.string().min(1, "El rol es requerido"),
  observaciones: z.string().optional(),
});

export type CreateAsignacionData = z.infer<typeof CreateAsignacionSchema>;

export const UpdateAsignacionSchema = CreateAsignacionSchema.partial();

export type UpdateAsignacionData = z.infer<typeof UpdateAsignacionSchema>;

/**
 * API response schema for asignacion data from Django REST API.
 */
export const AsignacionResponseSchema = z.object({
  id: z.string().uuid(),
  tramite_id: z.string().uuid(),
  usuario_id: z.string().uuid(),
  rol: z.string(),
  observaciones: z.string().nullable(),
  estado: z.string(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
});

export type AsignacionResponse = z.infer<typeof AsignacionResponseSchema>;

// ── Bandeja / Periodo Schemas ────────────────────────────────────────────────

/**
 * Nested solicitud summary for PeriodoItemSchema.
 */
const PeriodoSolicitudSummarySchema = z.object({
  id: z.string().uuid(),
  id_publico: z.string(),
  asunto: z.string(),
});

export type PeriodoSolicitudSummary = z.infer<typeof PeriodoSolicitudSummarySchema>;

/**
 * PeriodoItemSchema — fields for the bandeja (inbox) view.
 * Represents a period assigned to an area in the user's bandeja operativa.
 */
export const PeriodoItemSchema = z.object({
  id: z.string().uuid(),
  numero_ciclo: z.number(),
  tipo_participacion: z.enum(["PRINCIPAL", "ADJUNTA"]),
  estado: z.enum(["ABIERTO", "CERRADO"]),
  estado_institucional: z
    .enum(["PENDIENTE", "EN_GESTION", "FINALIZADO", "CANCELADO"])
    .nullable(),
  fecha_inicio: z.string().datetime().nullable(),
  fecha_fin: z.string().datetime().nullable(),
  area_nombre: z.string(),
  solicitud: PeriodoSolicitudSummarySchema,
  participo: z.boolean(),
});

export type PeriodoItem = z.infer<typeof PeriodoItemSchema>;

/**
 * Paginated bandeja response envelope.
 * Matches backend contract: ApiResponse[PaginatedData[PeriodoItem]]
 */
export const BandejaResponseSchema = z.object({
  success: z.boolean(),
  data: z
    .object({
      items: z.array(PeriodoItemSchema),
      total: z.number(),
      page: z.number(),
      page_size: z.number(),
      total_pages: z.number(),
    })
    .nullable(),
  error: z
    .object({
      code: z.string(),
      message: z.string(),
    })
    .nullable()
    .optional(),
});

export type BandejaResponse = z.infer<typeof BandejaResponseSchema>;
