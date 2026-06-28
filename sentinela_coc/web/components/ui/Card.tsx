import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

// Tarjeta del Design System. Si recibe onClick es operable por teclado (role=button +
// tabIndex + Enter/Espacio) con foco visible; el onKeyDown solo actúa cuando el foco está
// en la tarjeta misma (no en hijos interactivos como un checkbox anidado).
export function Card({
  className,
  children,
  onClick,
}: {
  className?: string;
  children: ReactNode;
  onClick?: () => void;
}) {
  const interactive = !!onClick;
  return (
    <div
      onClick={onClick}
      role={interactive ? "button" : undefined}
      tabIndex={interactive ? 0 : undefined}
      onKeyDown={
        interactive
          ? (e) => {
              if ((e.key === "Enter" || e.key === " ") && e.target === e.currentTarget) {
                e.preventDefault();
                onClick!();
              }
            }
          : undefined
      }
      className={cn(
        "rounded-card border border-slate-100 bg-surface p-4 shadow-card",
        interactive && "cursor-pointer transition active:scale-[.99] focus-ring",
        className,
      )}
    >
      {children}
    </div>
  );
}
