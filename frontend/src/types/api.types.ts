/**
 * Standard API error detail (matches backend ErrorDetail).
 */
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

/**
 * Standard API response wrapper (matches backend ApiResponse[T]).
 * Backend: { success: bool, data: T | None, error: ErrorDetail | None }
 */
export interface ApiResponse<T> {
  success: boolean;
  data: T | null;
  error?: ApiError;
}

// ── Shared Zod Schemas for Runtime Validation ──────────────────────────────────

import { z } from "zod";

/** Shared error detail schema — matches ApiError shape */
export const apiErrorSchema = z.object({
  code: z.string(),
  message: z.string(),
  details: z.record(z.string(), z.any()).optional(),
});

/**
 * Creates a full API response envelope schema wrapping any data payload schema.
 * Use this instead of duplicating { success, data, error } Zod objects per hook.
 *
 * @example
 * const schema = apiResponseSchema(z.object({ igv_valor: z.number() }));
 */
export function apiResponseSchema<T>(dataSchema: z.ZodType<T>) {
  return z.object({
    success: z.boolean(),
    data: dataSchema.nullable(),
    error: apiErrorSchema.nullable().optional(),
  });
}

/**
 * Standard paginated response — V2 Django contract.
 * Backend: { items, total, page, page_size, total_pages }
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/**
 * Generic list params for paginated endpoints.
 */
export interface ListParams {
  page?: number;
  pageSize?: number;
  search?: string;
  ordering?: string;
  [key: string]: unknown;
}
