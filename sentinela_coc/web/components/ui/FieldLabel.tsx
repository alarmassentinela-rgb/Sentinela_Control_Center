import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

// Etiqueta de campo del Design System. ÚNICA implementación de labels de formulario:
// fuerza la asociación label<->input (accesibilidad). No conoce el dominio.
export function FieldLabel({
  htmlFor,
  className,
  children,
}: {
  htmlFor: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <label htmlFor={htmlFor} className={cn("block text-aux font-medium text-ink", className)}>
      {children}
    </label>
  );
}
