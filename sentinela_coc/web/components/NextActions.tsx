"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Card } from "./ui/Card";
import { cn } from "@/lib/cn";
import type { NextAction } from "@/lib/types";

// Categorías (colapsables, colapsadas por defecto) para reducir altura.
const CATEGORIES = [
  { key: "payment_overdue", label: "Facturas vencidas" },
  { key: "invoice_due", label: "Facturas por pagar" },
  { key: "service_suspended", label: "Servicios suspendidos" },
  { key: "contract_pending_signature", label: "Contratos por firmar" },
];

const SEV: Record<string, string> = {
  high: "border-l-danger",
  medium: "border-l-warn",
  low: "border-l-slate-300",
};

export function NextActions({ actions }: { actions: NextAction[] }) {
  const router = useRouter();
  const [open, setOpen] = useState<string | null>(null); // colapsadas por defecto
  if (!actions?.length) return null;

  return (
    <section className="space-y-2">
      <h2 className="px-1 text-aux font-semibold text-muted">Próximas acciones</h2>
      {CATEGORIES.map((c) => {
        const items = actions.filter((a) => a.type === c.key);
        if (!items.length) return null;
        const isOpen = open === c.key;
        return (
          <div key={c.key} className="overflow-hidden rounded-card border border-slate-100 bg-surface">
            <button
              type="button"
              onClick={() => setOpen(isOpen ? null : c.key)}
              aria-expanded={isOpen}
              className="focus-ring flex w-full items-center gap-2 px-4 py-3 text-left text-aux font-semibold text-ink"
            >
              <span className={cn("text-caption text-muted transition-transform", isOpen && "rotate-90")}>▶</span>
              {c.label} ({items.length})
            </button>
            {isOpen && (
              <div className="space-y-2 px-3 pb-3">
                {items.map((a) => (
                  <Card key={a.key} onClick={() => router.push(a.target)} className={cn("border-l-4", SEV[a.severity] || SEV.low)}>
                    <div className="flex items-start gap-3">
                      <div className="min-w-0 flex-1">
                        <p className="text-aux font-semibold text-ink">{a.title}</p>
                        <p className="text-caption text-muted">{a.detail}</p>
                      </div>
                      <div className="text-muted">›</div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </section>
  );
}
