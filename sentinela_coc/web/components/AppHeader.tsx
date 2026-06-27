"use client";
import { useEffect, useState } from "react";

import { useQuery } from "@/hooks/useQuery";
import { apiGet, apiGetEnvelope } from "@/lib/api";
import { cn } from "@/lib/cn";
import { loadTheme } from "@/lib/theme";
import type { Dashboard, Theme } from "@/lib/types";

type Me = { id: number; name: string };

// Estado general del cliente derivado del dashboard (sin backend nuevo).
function generalState(d?: Dashboard) {
  if (!d) return null;
  if ((d.billing?.overdue_amount || 0) > 0) return { label: "Adeudo", cls: "bg-red-100 text-red-700" };
  if ((d.services?.suspended || 0) > 0) return { label: "Suspendido", cls: "bg-amber-100 text-amber-700" };
  return { label: "Activo", cls: "bg-green-100 text-green-700" };
}

// Encabezado institucional compacto, presente en todas las pantallas autenticadas.
export function AppHeader() {
  const me = useQuery(() => apiGet<Me>("/v1/me"), []);
  const dash = useQuery(() => apiGetEnvelope<Dashboard>("/v1/dashboard"), []);
  const [theme, setTheme] = useState<Theme | null>(null);
  useEffect(() => {
    loadTheme().then(setTheme);
  }, []);

  const appName = theme?.app_name || "Sentinela";
  const firstName = (me.data?.name || "").split(" ")[0];
  const st = generalState(dash.data?.data);
  const lastRefresh = dash.data?.meta?.last_refresh;
  const updated = lastRefresh
    ? new Date(lastRefresh).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
      <div className="flex items-center justify-between gap-2 px-4 py-2">
        <div className="flex min-w-0 items-center gap-2">
          {theme?.logo_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={theme.logo_url} alt={appName} className="h-7 w-auto" />
          ) : (
            <div className="grid h-7 w-7 place-items-center rounded-lg bg-brand text-sm text-white" aria-hidden>🛡️</div>
          )}
          <div className="leading-tight">
            <p className="text-sm font-bold text-ink">{appName}</p>
            <p className="-mt-0.5 text-[10px] text-muted">Portal del Cliente</p>
          </div>
        </div>

        <div className="min-w-0 text-right leading-tight">
          <div className="flex items-center justify-end gap-2">
            {me.data && <p className="max-w-[42vw] truncate text-xs font-semibold text-ink sm:max-w-none">Hola, {firstName}</p>}
            {st && <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-semibold", st.cls)}>{st.label}</span>}
          </div>
          <p className="text-[10px] text-muted">
            {me.data ? `Cliente #${me.data.id}` : "—"}
            {updated ? ` · Actualizado ${updated}` : ""}
          </p>
        </div>
      </div>
    </header>
  );
}
