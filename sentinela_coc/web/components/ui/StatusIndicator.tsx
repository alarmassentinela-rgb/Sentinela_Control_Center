import { cn } from "@/lib/cn";

// Indicador de estado del DESIGN SYSTEM (semáforo). Reutilizable en cualquier pantalla
// (Dashboard, Servicios, Notificaciones, …). Decisiones de diseño:
//  - COLOR por TONO semántico -> un único mapa (no se duplica el color por pantalla).
//  - TAMAÑO por token (o className) -> cambiar el tamaño = cambiar el prop/constante,
//    sin modificar este componente ni el SVG.
//  - halo opcional (puntos pequeños inline no lo necesitan).
export type StatusTone = "ok" | "warn" | "danger" | "neutral";

const TONE_COLOR: Record<StatusTone, string> = {
  ok: "text-green-500",
  warn: "text-amber-500",
  danger: "text-red-500",
  neutral: "text-slate-400",
};

// Única fuente de tamaños del indicador. Añadir/ajustar aquí, no en los componentes.
const SIZE: Record<string, string> = {
  sm: "h-2.5 w-2.5",
  md: "h-5 w-5",
  lg: "h-8 w-8",
  hero: "h-14 w-14 lg:h-24 lg:w-24",
};

export function StatusIndicator({
  tone = "ok",
  size = "md",
  halo = true,
  className,
}: {
  tone?: StatusTone;
  size?: keyof typeof SIZE;
  halo?: boolean;
  className?: string;
}) {
  return (
    <svg viewBox="0 0 24 24" className={cn(SIZE[size], "shrink-0", TONE_COLOR[tone], className)} aria-hidden>
      {halo && <circle cx="12" cy="12" r="10.5" fill="currentColor" opacity="0.18" />}
      <circle cx="12" cy="12" r={halo ? 7.5 : 10} fill="currentColor" />
    </svg>
  );
}
