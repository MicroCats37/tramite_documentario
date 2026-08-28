import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useApiQuery, usePagination } from "@/hooks";
import {
  NotificationItemSchema,
  NotificacionListResponseSchema,
  type MarcarVistaResponse,
  type DescartarNotificacionResponse,
  type NotificacionListResponse,
  type NotificationItem,
} from "../schemas/notificacion.schema";
import {
  getNotificaciones,
  marcarVista,
  descartarNotificacion,
  type GetNotificacionesParams,
} from "../services/notificacion.service";

// ── Query Key ─────────────────────────────────────────────────────────────────

const NOTIFICACIONES_QUERY_KEY = ["notificaciones"] as const;

// ── useNotificaciones ─────────────────────────────────────────────────────────

/**
 * Hook to fetch paginated notifications list.
 * Combines usePagination (page, pageSize) with useApiQuery.
 * Returns items + total + totalPages via select transform on the ApiResponse envelope.
 * Loading the list does NOT mark notifications as viewed.
 */
export function useNotificaciones(initialPage = 1) {
  const { page, pageSize, onPageChange, onPageSizeChange, paginationParams } =
    usePagination({ initialPage });

  const query = useApiQuery<
    NotificacionListResponse,
    { items: NotificationItem[]; total: number; totalPages: number }
  >({
    queryKey: NOTIFICACIONES_QUERY_KEY,
    url: "/notificaciones",
    schema: NotificacionListResponseSchema,
    params: paginationParams,
    queryOptions: {
      select: (response) => {
        const data = response.data;
        return {
          items: data?.items ?? [],
          total: data?.total ?? 0,
          totalPages: data?.total_pages ?? 0,
        };
      },
    },
  });

  return {
    ...query,
    items: query.data?.items ?? [],
    total: query.data?.total ?? 0,
    totalPages: query.data?.totalPages ?? 0,
    page,
    pageSize,
    onPageChange,
    onPageSizeChange,
  };
}

// ── useMarkVista ──────────────────────────────────────────────────────────────

/**
 * Mutation hook to mark a notification as viewed (NO_VISTA → VISTA).
 * Should be called once when the notification is deliberately shown.
 * Invalidates the notificaciones list cache on success.
 */
export function useMarkVista() {
  const queryClient = useQueryClient();

  return useMutation<MarcarVistaResponse, unknown, string>({
    mutationFn: (id: string) => marcarVista(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: NOTIFICACIONES_QUERY_KEY });
    },
  });
}

// ── useDescartarNotificacion ─────────────────────────────────────────────────

/**
 * Mutation hook to discard a notification.
 * Only affects the current user's individual interaction record.
 * Invalidates the notificaciones list cache on success.
 */
export function useDescartarNotificacion() {
  const queryClient = useQueryClient();

  return useMutation<DescartarNotificacionResponse, unknown, string>({
    mutationFn: (id: string) => descartarNotificacion(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: NOTIFICACIONES_QUERY_KEY });
    },
  });
}
