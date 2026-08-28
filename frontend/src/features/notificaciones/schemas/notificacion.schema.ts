import { z } from "zod";

// ── Estado Individual de Notificación ──────────────────────────────────────────

/**
 * Backend: NO_VISTA | VISTA | ABIERTA | DESCARTADA
 * Representa el estado individual de la interacción del usuario con la notificación.
 */
export const ESTADO_NOTIFICACION_VALUES = [
  "NO_VISTA",
  "VISTA",
  "ABIERTA",
  "DESCARTADA",
] as const;

export type EstadoNotificacionIndividual =
  (typeof ESTADO_NOTIFICACION_VALUES)[number];

// ── Notification Item Schema ───────────────────────────────────────────────────

/**
 * NotificationItemSchema — item fields for notification list display.
 * Includes: título, tipo de evento, fecha, área destinataria,
 * solicitud/expediente resumidos, período contextual, estado individual
 * e indicador de participación del actor.
 */
export const NotificationItemSchema = z.object({
  id: z.string().uuid(),
  titulo: z.string(),
  tipo_evento: z.string(),
  fecha_evento: z.string().datetime(),
  area_nombre: z.string(),
  solicitud_id_publico: z.string().nullable(),
  solicitud_asunto: z.string().nullable(),
  periodo_ciclo: z.number().nullable(),
  periodo_activo: z.boolean(),
  estado_individual: z.enum(ESTADO_NOTIFICACION_VALUES),
  participo: z.boolean(),
});

export type NotificationItem = z.infer<typeof NotificationItemSchema>;

// ── Notification Detail Schema ────────────────────────────────────────────────

/**
 * NotificationDetailSchema — full notification detail for /notificaciones/[id].
 * Includes full description and redirect context.
 */
export const NotificationDetailSchema = NotificationItemSchema.extend({
  descripcion: z.string().nullable(),
  solicitud_id: z.string().uuid().nullable(),
});

export type NotificationDetail = z.infer<typeof NotificationDetailSchema>;

// ── API Response Schemas ──────────────────────────────────────────────────────

/**
 * Paginated response wrapper for Notificaciones list.
 * Matches backend contract: ApiResponse[PaginatedData[T]]
 */
export const NotificacionListResponseSchema = z.object({
  success: z.boolean(),
  data: z
    .object({
      items: z.array(NotificationItemSchema),
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

export type NotificacionListResponse = z.infer<
  typeof NotificacionListResponseSchema
>;

// ── Action Response Schemas ────────────────────────────────────────────────────

/**
 * Response after marking a notification as viewed.
 */
export const MarcarVistaResponseSchema = z.object({
  success: z.boolean(),
  data: z
    .object({
      id: z.string().uuid(),
      estado_individual: z.enum(ESTADO_NOTIFICACION_VALUES),
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

export type MarcarVistaResponse = z.infer<typeof MarcarVistaResponseSchema>;

/**
 * Response after discarding a notification.
 */
export const DescartarNotificacionResponseSchema = z.object({
  success: z.boolean(),
  data: z
    .object({
      id: z.string().uuid(),
      estado_individual: z.enum(ESTADO_NOTIFICACION_VALUES),
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

export type DescartarNotificacionResponse = z.infer<
  typeof DescartarNotificacionResponseSchema
>;
