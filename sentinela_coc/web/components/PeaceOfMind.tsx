import { cn } from "@/lib/cn";

// Elemento CENTRAL del Dashboard: "Estado de Tranquilidad".
// Composición: columna flex con UN solo gap entre el indicador y el grupo de texto
// (las dos líneas van agrupadas y juntas). El indicador es un SVG propio (no emoji) ->
// apariencia IDÉNTICA en Windows/macOS/Android/iPhone y caja con métrica predecible,
// así la separación no depende del tamaño del icono ni de la tipografía del sistema.
const STYLE: Record<string, { bg: string; ring: string; dot: string }> = {
  tranquilo: { bg: "bg-green-50", ring: "ring-green-200", dot: "text-green-500" },
  atencion: { bg: "bg-amber-50", ring: "ring-amber-200", dot: "text-amber-500" },
  alerta: { bg: "bg-red-50", ring: "ring-red-200", dot: "text-red-500" },
};

export function PeaceOfMind({ status, label }: { status: string; label: string }) {
  const s = STYLE[status] || STYLE.tranquilo;
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-3 rounded-xl2 p-6 text-center ring-1 lg:h-full lg:gap-5 lg:p-12",
        s.bg,
        s.ring,
      )}
    >
      {/* Indicador SVG propio (tamaño/protagonismo por clases; halo + disco). */}
      <svg viewBox="0 0 24 24" className={cn("h-14 w-14 shrink-0 lg:h-24 lg:w-24", s.dot)} aria-hidden>
        <circle cx="12" cy="12" r="10.5" fill="currentColor" opacity="0.18" />
        <circle cx="12" cy="12" r="7.5" fill="currentColor" />
      </svg>
      <div className="flex flex-col gap-0.5">
        <p className="text-[11px] uppercase tracking-wide text-muted lg:text-sm">Estado de tranquilidad</p>
        <p className="text-lg font-bold text-ink lg:text-3xl">{label}</p>
      </div>
    </div>
  );
}
