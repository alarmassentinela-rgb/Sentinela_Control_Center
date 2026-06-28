import { StatusIndicator, type StatusTone } from "@/components/ui/StatusIndicator";
import { cn } from "@/lib/cn";

// Elemento CENTRAL del Dashboard: "Estado de Tranquilidad".
// Composición: columna flex con UN solo gap entre el indicador y el grupo de texto
// (las dos líneas agrupadas y juntas). El indicador es el componente del Design System
// <StatusIndicator> (SVG reutilizable, color por tono, tamaño por token) -> apariencia
// idéntica en todas las plataformas y separación independiente del tamaño del icono.
// Solo el fondo/anillo de la tarjeta es propio del hero.
const CARD: Record<string, { bg: string; ring: string; tone: StatusTone }> = {
  tranquilo: { bg: "bg-green-50", ring: "ring-green-200", tone: "ok" },
  atencion: { bg: "bg-amber-50", ring: "ring-amber-200", tone: "warn" },
  alerta: { bg: "bg-red-50", ring: "ring-red-200", tone: "danger" },
};

export function PeaceOfMind({ status, label }: { status: string; label: string }) {
  const s = CARD[status] || CARD.tranquilo;
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-xl2 p-6 text-center ring-1 lg:h-full lg:gap-5 lg:p-12",
        s.bg,
        s.ring,
      )}
    >
      <StatusIndicator tone={s.tone} size="xl" />
      <div className="flex flex-col gap-0.5">
        <p className="text-[11px] uppercase tracking-wide text-muted lg:text-sm">Estado de tranquilidad</p>
        <p className="text-lg font-bold text-ink lg:text-3xl">{label}</p>
      </div>
    </div>
  );
}
