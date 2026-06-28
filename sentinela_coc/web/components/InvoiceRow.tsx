"use client";
import { useRouter } from "next/navigation";

import { Badge, type BadgeTone } from "./ui/Badge";
import { Card } from "./ui/Card";
import { formatDate, money } from "@/lib/format";
import type { Invoice } from "@/lib/types";

// `onToggle` activa el modo selección (checkbox) para facturas por pagar.
export function InvoiceRow({
  inv,
  selected,
  onToggle,
}: {
  inv: Invoice;
  selected?: boolean;
  onToggle?: (id: number) => void;
}) {
  const router = useRouter();
  const paid = inv.payment_state === "paid";
  // "Vencida" = no pagada y su fecha de vencimiento ya pasó (cálculo en SPA).
  const overdue = !paid && !!inv.due_date && new Date(inv.due_date) < new Date(new Date().toDateString());
  const docLabel = inv.doc_type === "factura" ? "Factura" : "Remisión";
  const stTone: BadgeTone = paid ? "ok" : overdue ? "danger" : "warn";
  const stLabel = paid ? "Pagada" : overdue ? "Vencida" : "Por pagar";
  const selectable = !!onToggle && !paid && (inv.amount_due || 0) > 0;

  return (
    <Card onClick={() => router.push(`/facturacion/${inv.id}`)}>
      <div className="flex items-center gap-3">
        {selectable && (
          <input
            type="checkbox"
            checked={!!selected}
            onClick={(e) => e.stopPropagation()}
            onChange={() => onToggle!(inv.id)}
            className="focus-ring h-5 w-5 shrink-0 accent-[color:var(--brand-primary)]"
            aria-label={`Seleccionar ${inv.number || docLabel}`}
          />
        )}
        <div className="flex min-w-0 flex-1 items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate font-semibold text-ink">{inv.number || docLabel}</p>
            <p className="text-caption text-muted">
              {formatDate(inv.date)} · {docLabel}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <p className="font-semibold text-ink">{money(inv.amount_total, inv.currency)}</p>
            <Badge tone={stTone}>{stLabel}</Badge>
          </div>
        </div>
      </div>
    </Card>
  );
}
