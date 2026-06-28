"use client";
import { useCallback, useEffect, useMemo, useState } from "react";

import { apiGet } from "@/lib/api";
import { friendlyError } from "@/lib/format";
import type { Paged } from "@/lib/types";

// Hook GENÉRICO de paginación incremental ("cargar más"). No conoce el dominio: recibe
// endpoint + params + pageSize y acumula páginas. Reutilizable en cualquier listado.
export function usePaged<T>(
  endpoint: string,
  params: Record<string, string | number> = {},
  pageSize = 20,
) {
  const [items, setItems] = useState<T[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const paramsKey = JSON.stringify(params);

  const url = useCallback(
    (p: number) => {
      const u = new URLSearchParams();
      Object.entries(params).forEach(([k, v]) => u.set(k, String(v)));
      u.set("page", String(p));
      u.set("limit", String(pageSize));
      return `${endpoint}?${u.toString()}`;
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [endpoint, paramsKey, pageSize],
  );

  const load = useCallback(
    async (p: number, append: boolean) => {
      setLoading(true);
      setError(null);
      try {
        const res = await apiGet<Paged<T>>(url(p));
        setTotal(res.count);
        setItems((prev) => (append ? [...prev, ...res.items] : res.items));
        setPage(p);
      } catch (e) {
        setError(friendlyError(e));
      } finally {
        setLoading(false);
      }
    },
    [url],
  );

  useEffect(() => {
    load(1, false);
  }, [load]);

  const hasMore = items.length < total;
  const loadMore = useCallback(() => {
    if (hasMore && !loading) load(page + 1, true);
  }, [hasMore, loading, page, load]);
  const reload = useCallback(() => load(1, false), [load]);

  return useMemo(
    () => ({ items, total, hasMore, loading, error, loadMore, reload }),
    [items, total, hasMore, loading, error, loadMore, reload],
  );
}
