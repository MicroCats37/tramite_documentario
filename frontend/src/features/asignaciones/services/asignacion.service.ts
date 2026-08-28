import api from "@/lib/api";
import type {
  AsignacionResponse,
  BandejaResponse,
  CreateAsignacionData,
  UpdateAsignacionData,
} from "../schemas/asignacion.schema";

/**
 * Asignacion service - consumes Django REST API via Axios.
 */

// ── Legacy CRUD ──────────────────────────────────────────────────────────────

export async function getAsignaciones(): Promise<AsignacionResponse[]> {
  const response = await api.get<AsignacionResponse[]>("/asignaciones/");
  return response.data;
}

export async function getAsignacion(id: string): Promise<AsignacionResponse> {
  const response = await api.get<AsignacionResponse>(`/asignaciones/${id}/`);
  return response.data;
}

export async function createAsignacion(
  data: CreateAsignacionData,
): Promise<AsignacionResponse> {
  const response = await api.post<AsignacionResponse>("/asignaciones/", data);
  return response.data;
}

export async function updateAsignacion(
  id: string,
  data: UpdateAsignacionData,
): Promise<AsignacionResponse> {
  const response = await api.patch<AsignacionResponse>(`/asignaciones/${id}/`, data);
  return response.data;
}

export async function deleteAsignacion(id: string): Promise<void> {
  await api.delete(`/asignaciones/${id}/`);
}

// ── Bandeja / Periodos ──────────────────────────────────────────────────────

export interface GetPeriodosBandejaParams {
  page?: number;
  page_size?: number;
  estado?: string;
  area_id?: string;
}

/**
 * Fetches the user's bandeja (inbox) of periods.
 * Returns paginated PeriodoItems grouped by area.
 */
export async function getPeriodosBandeja(
  params: GetPeriodosBandejaParams = {},
): Promise<BandejaResponse> {
  const response = await api.get<BandejaResponse>("/periodos/bandeja", {
    params,
  });
  return response.data;
}

/**
 * Takes a period (marks the user as participant).
 * POST /api/periodos/{id}/tomar
 */
export async function tomarPeriodo(id: string): Promise<unknown> {
  const response = await api.post<unknown>(`/periodos/${id}/tomar`);
  return response.data;
}
