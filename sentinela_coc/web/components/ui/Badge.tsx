import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

// Chip de estado del Design System. ÚNICA implementación de chips/estados del portal:
// ningún componente debe volver a definir verde/amarillo/rojo a mano. No conoce el dominio:
// solo recibe un TONO semántico + contenido.
export type BadgeTone = "ok" | "warn" | "danger" | "neutral" | "info";

const TONE: Record<BadgeTone, string> = {
  ok: "bg-green-100 text-green-700",
  warn: "bg-amber-100 text-amber-700",
  danger: "bg-red-100 text-red-700",
  neutral: "bg-slate-100 text-slate-600",
  info: "bg-blue-100 text-blue-700",
};

export function Badge({
  tone = "neutral",
  className,
  children,
}: {
  tone?: BadgeTone;
  className?: string;
  children: ReactNode;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-pill px-2.5 py-1 text-caption font-semibold",
        TONE[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
