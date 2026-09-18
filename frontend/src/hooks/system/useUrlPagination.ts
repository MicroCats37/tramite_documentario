/**
 * useUrlPagination — pagination state synchronized with URL search params.
 *
 * Reads initial page/page_size from the URL on mount.
 * Updates the URL (via router.replace) whenever page or pageSize changes.
 * This ensures page reload and share preserve the user's position.
 *
 * Usage:
 *   const { page, pageSize, onPageChange, onPageSizeChange, paginationParams } = useUrlPagination();
 */

import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

const DEFAULT_PAGE = 1;
const DEFAULT_PAGE_SIZE = 10;
const MAX_PAGE_SIZE = 100;

interface UseUrlPaginationOptions {
  initialPageSize?: number;
}

export function useUrlPagination(options: UseUrlPaginationOptions = {}) {
  const { initialPageSize = DEFAULT_PAGE_SIZE } = options;
  const router = useRouter();
  const searchParams = useSearchParams();

  // Read current values from URL, defaulting to 1 and initialPageSize
  const page = useMemo(() => {
    const p = searchParams.get("page");
    const parsed = p ? parseInt(p, 10) : DEFAULT_PAGE;
    return Number.isFinite(parsed) && parsed > 0 ? parsed : DEFAULT_PAGE;
  }, [searchParams]);

  const pageSize = useMemo(() => {
    const ps = searchParams.get("page_size");
    const parsed = ps ? parseInt(ps, 10) : initialPageSize;
    return Number.isFinite(parsed) && parsed > 0 && parsed <= MAX_PAGE_SIZE
      ? parsed
      : initialPageSize;
  }, [searchParams, initialPageSize]);

  /** Build updated search params, removing page when resetting to 1 */
  const buildParams = useCallback(
    (updates: Record<string, string | number | null>) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(updates)) {
        if (value === null || value === "" || value === undefined) {
          params.delete(key);
        } else {
          params.set(key, String(value));
        }
      }
      return params.toString();
    },
    [searchParams],
  );

  const onPageChange = useCallback(
    (newPage: number) => {
      const qs = buildParams({ page: newPage });
      router.replace(`?${qs}`, { scroll: false });
    },
    [buildParams, router],
  );

  const onPageSizeChange = useCallback(
    (newPageSize: number) => {
      const clampedSize = Math.min(Math.max(newPageSize, 1), MAX_PAGE_SIZE);
      const qs = buildParams({ page_size: clampedSize, page: 1 });
      router.replace(`?${qs}`, { scroll: false });
    },
    [buildParams, router],
  );

  /** Convenience: push a filter change that resets to page 1 */
  const resetPageAndPush = useCallback(
    (updates: Record<string, string | number | null>) => {
      // When setting new filter values, page=1 is the default unless
      // the update explicitly includes a page key.
      const safeUpdates = { page: 1, ...updates };
      const qs = buildParams(safeUpdates);
      router.replace(`?${qs}`, { scroll: false });
    },
    [buildParams, router],
  );

  return {
    page,
    pageSize,
    onPageChange,
    onPageSizeChange,
    resetPageAndPush,
    paginationParams: {
      page,
      page_size: pageSize,
    },
  };
}
