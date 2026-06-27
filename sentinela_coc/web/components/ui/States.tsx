"use client";
import type { ReactNode } from "react";

import { Button } from "./Button";

// Mensajes de error amigables (nunca técnicos) + acción de reintento.
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-xl2 bg-white border border-slate-100 p-6 text-center">
      <div className="text-3xl" aria-hidden>😕</div>
      <p className="text-sm text-muted">{message}</p>
      {onRetry && (
        <Button variant="secondary" onClick={onRetry}>
          Reintentar
        </Button>
      )}
    </div>
  );
}

export function EmptyState({ icon = "📭", title, hint }: { icon?: string; title: string; hint?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 p-8 text-center">
      <div className="text-4xl" aria-hidden>{icon}</div>
      <p className="font-medium text-ink">{title}</p>
      {hint && <p className="text-sm text-muted">{hint}</p>}
    </div>
  );
}
