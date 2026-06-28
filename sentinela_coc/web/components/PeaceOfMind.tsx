import { StatusIndicator, type StatusTone } from "@/components/ui/StatusIndicator";
import { cn } from "@/lib/cn";

// Elemento CENTRAL del Dashboard: "Estado de Tranquilidad".
// Mensaje al cliente (voz humana) derivado del `status` en la SPA (no backend), distinto del
// chip técnico del header. Composición: columna flex con UN solo gap entre el indicador
// (<StatusIndicator> del DS) y el grupo de texto.
const CARD: Record<string, { bg: string; ring: string; tone: StatusTone; label: string }> = {
  tranquilo: { bg: "bg-green-50", ring: "ring-green-200", tone: "ok", label: "Todo en orden" },
  atencion: { bg: "bg-amber-50", ring: "ring-amber-200", tone: "warn", label: "Requiere tu atención" },
  alerta: { bg: "bg-red-50", ring: "ring-red-200", tone: "danger", label: "Servicio suspendido" },
};

export function PeaceOfMind({ status }: { status: string }) {
  const s = CARD[status] || CARD.tranquilo;
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-card p-6 text-center ring-1 lg:h-full lg:gap-5 lg:p-12",
        s.bg,
        s.ring,
      )}
    >
      <StatusIndicator tone={s.tone} size="xl" />
      <div className="flex flex-col gap-0.5">
        <p className="text-caption uppercase tracking-wide text-muted lg:text-aux">Estado de tranquilidad</p>
        <p className="text-subtitle font-bold text-ink lg:text-hero">{s.label}</p>
      </div>
    </div>
  );
}
