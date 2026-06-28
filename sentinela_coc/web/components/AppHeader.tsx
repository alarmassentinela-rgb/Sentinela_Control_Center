"use client";
import { BrandMark } from "@/components/BrandMark";
import { Badge } from "@/components/ui/Badge";
import { BellIcon, SparklesIcon } from "@/components/ui/icons";
import { StatusIndicator, type StatusTone } from "@/components/ui/StatusIndicator";
import { useQuery } from "@/hooks/useQuery";
import { accountStatus } from "@/lib/accountState";
import { apiGet, apiGetEnvelope } from "@/lib/api";
import type { Dashboard } from "@/lib/types";

type Me = { id: number; name: string };

// Chip TÉCNICO derivado del estado de cuenta ÚNICO (mismo que el hero, distinto registro).
const STATE_CHIP: Record<string, { label: string; tone: StatusTone }> = {
  tranquilo: { label: "Activo", tone: "ok" },
  atencion: { label: "Atención requerida", tone: "warn" },
  alerta: { label: "Suspendido", tone: "danger" },
};

export function AppHeader() {
  const me = useQuery(() => apiGet<Me>("/v1/me"), []);
  const dash = useQuery(() => apiGetEnvelope<Dashboard>("/v1/dashboard"), []);
  const firstName = (me.data?.name || "").split(" ")[0];
  const st = dash.data?.data ? STATE_CHIP[accountStatus(dash.data.data)] : null;
  const lastRefresh = dash.data?.meta?.last_refresh;
  const updated = lastRefresh
    ? new Date(lastRefresh).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <header className="sticky top-0 z-header border-b border-slate-200 bg-white/95 backdrop-blur">
      {/* Barra compacta. Izquierda: identidad (BrandMark). Derecha: acciones reservadas
          (deshabilitadas, a futuro solo se habilitan) + bloque de cliente con chip de estado
          + avatar. En móvil el estado se reduce a un punto (evita desbordes con etiquetas largas). */}
      <div className="flex items-center gap-3 px-4 py-1">
        <BrandMark layout="header" />

        <div className="ml-auto flex items-center gap-2">
          <div className="hidden items-center gap-0.5 sm:flex">
            <button type="button" disabled aria-label="Notificaciones (próximamente)"
                    className="focus-ring grid h-8 w-8 place-items-center rounded-pill text-slate-500 transition hover:bg-slate-100 disabled:hover:bg-transparent">
              <BellIcon className="h-5 w-5" />
            </button>
            <button type="button" disabled aria-label="Asistente IA (próximamente)"
                    className="focus-ring grid h-8 w-8 place-items-center rounded-pill text-slate-500 transition hover:bg-slate-100 disabled:hover:bg-transparent">
              <SparklesIcon className="h-5 w-5" />
            </button>
          </div>

          {/* Móvil: solo el indicador de estado (punto). */}
          {st && <StatusIndicator tone={st.tone} size="md" halo={false} className="sm:hidden" />}

          {me.data && (
            <>
              <div className="hidden items-center gap-2.5 rounded-pill sm:flex sm:bg-slate-50 sm:px-3 sm:py-1">
                <div className="text-right leading-tight">
                  <p className="whitespace-nowrap text-caption font-semibold text-ink">Hola, {firstName}</p>
                  <p className="whitespace-nowrap text-caption text-muted">
                    Cliente #{me.data.id}{updated ? ` · Actualizado ${updated}` : ""}
                  </p>
                </div>
                {st && <Badge tone={st.tone}>{st.label}</Badge>}
              </div>
              <button type="button" disabled aria-label="Perfil (próximamente)"
                      className="focus-ring hidden h-8 w-8 shrink-0 place-items-center rounded-pill bg-slate-100 text-caption font-semibold text-slate-600 ring-1 ring-slate-200 sm:grid">
                {(firstName?.[0] || "·").toUpperCase()}
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
