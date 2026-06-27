import { cn } from "@/lib/cn";

// Elemento CENTRAL del Dashboard: "Estado de Tranquilidad".
const STYLE: Record<string, { bg: string; ring: string; icon: string }> = {
  tranquilo: { bg: "bg-green-50", ring: "ring-green-200", icon: "🟢" },
  atencion: { bg: "bg-amber-50", ring: "ring-amber-200", icon: "🟡" },
  alerta: { bg: "bg-red-50", ring: "ring-red-200", icon: "🔴" },
};

export function PeaceOfMind({ status, label }: { status: string; label: string }) {
  const s = STYLE[status] || STYLE.tranquilo;
  return (
    <div
      className={cn(
        "rounded-xl2 ring-1 p-6 text-center lg:flex lg:h-full lg:flex-col lg:justify-center lg:p-12",
        s.bg,
        s.ring,
      )}
    >
      <div className="mb-1 text-5xl lg:text-8xl" aria-hidden>{s.icon}</div>
      <p className="text-[11px] uppercase tracking-wide text-muted lg:text-sm">Estado de tranquilidad</p>
      <p className="text-lg font-bold text-ink lg:text-3xl">{label}</p>
    </div>
  );
}
