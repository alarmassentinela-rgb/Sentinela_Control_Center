"use client";
import { BrandMark } from "@/components/BrandMark";
import { BellIcon, SparklesIcon } from "@/components/ui/icons";
import { useQuery } from "@/hooks/useQuery";
import { apiGet, apiGetEnvelope } from "@/lib/api";
import { cn } from "@/lib/cn";
import type { Dashboard } from "@/lib/types";

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
  const firstName = (me.data?.name || "").split(" ")[0];
  const st = generalState(dash.data?.data);
  const lastRefresh = dash.data?.meta?.last_refresh;
  const updated = lastRefresh
    ? new Date(lastRefresh).toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/95 backdrop-blur">
      {/* Barra COMPACTA (py-1). Identidad = Odoo (logo con proporción intacta) + título
          principal alineados como una sola unidad. Derecha: acciones reservadas (visual)
          + bloque de cliente cohesivo con el estado destacado + avatar de perfil. */}
      <div className="flex items-center gap-3 px-4 py-1">
        <BrandMark layout="header" />

        <div className="ml-auto flex items-center gap-2">
          {/* Acciones reservadas: botones YA presentes (deshabilitados); a futuro solo se
              habilitan, sin mover el layout. Iconografía SVG (no emojis). Solo tablet/escritorio. */}
          <div className="hidden items-center gap-0.5 sm:flex">
            <button type="button" disabled title="Notificaciones (próximamente)"
                    className="grid h-8 w-8 place-items-center rounded-full text-slate-400 transition hover:bg-slate-100 disabled:hover:bg-transparent">
              <BellIcon className="h-5 w-5" />
            </button>
            <button type="button" disabled title="Asistente IA (próximamente)"
                    className="grid h-8 w-8 place-items-center rounded-full text-slate-400 transition hover:bg-slate-100 disabled:hover:bg-transparent">
              <SparklesIcon className="h-5 w-5" />
            </button>
          </div>
          {me.data && (
            <>
              {/* Bloque de cliente cohesivo en tablet/escritorio; en móvil solo el estado. */}
              <div className="flex items-center gap-2.5 rounded-full sm:bg-slate-50 sm:px-3 sm:py-1">
                <div className="hidden text-right leading-tight sm:block">
                  <p className="whitespace-nowrap text-xs font-semibold text-ink">Hola, {firstName}</p>
                  <p className="whitespace-nowrap text-[10px] text-muted">
                    Cliente #{me.data.id}{updated ? ` · Actualizado ${updated}` : ""}
                  </p>
                </div>
                {st && (
                  <span className={cn("inline-flex justify-center rounded-full px-2.5 py-1 text-xs font-semibold sm:min-w-[5.5rem]", st.cls)}>
                    {st.label}
                  </span>
                )}
              </div>
              {/* Avatar de perfil (botón reservado): inicial en círculo con anillo — estilo empresarial. */}
              <button type="button" disabled title="Perfil (próximamente)"
                      className="hidden h-8 w-8 shrink-0 place-items-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600 ring-1 ring-slate-200 sm:grid">
                {(firstName?.[0] || "·").toUpperCase()}
              </button>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
