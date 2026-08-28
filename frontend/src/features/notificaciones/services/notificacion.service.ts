import api from "@/lib/api";
import type {
  DescartarNotificacionResponse,
  MarcarVistaResponse,
  NotificacionListResponse,
} from "../schemas/notificacion.schema";

// ── Notificaciones Service ─────────────────────────────────────────────────────

/**
 * Notificaciones service — consumes Django REST API via Axios.
 * Follows naming convention: {action}{Resource}() → camelCase
 */

export interface GetNotificacionesParams {
  page?: number;
  page_size?: number;
  /** Filter by status: NO_VISTA | VISTA | ABIERTA | DESCARTADA */
  estado?: string;
}

/**
 * Fetch paginated list of notifications for the current user.
 * Does NOT mark notifications as viewed on fetch — that is a separate action.
 */
export async function getNotificaciones(
  params: GetNotificacionesParams = {},
): Promise<NotificacionListResponse> {
  const response = await api.get<NotificacionListResponse>(
    "/notificaciones",
    { params },
  );
  return response.data;
}

/**
 * Mark a notification as viewed (NO_VISTA → VISTA).
 * Should be called once when the notification is deliberately shown.
 * Idempotent: calling again does not change the timestamp.
 */
export async function marcarVista(
  id: string,
): Promise<MarcarVistaResponse> {
  const response = await api.post<MarcarVistaResponse>(
    `/notificaciones/${id}/vista`,
  );
  return response.data;
}

/**
 * Discard a notification (removes it from the user's active view).
 * Only affects the current user's individual interaction record.
 */
export async function descartarNotificacion(
  id: string,
): Promise<DescartarNotificacionResponse> {
  const response = await api.post<DescartarNotificacionResponse>(
    `/notificaciones/${id}/descartar`,
  );
  return response.data;
}
