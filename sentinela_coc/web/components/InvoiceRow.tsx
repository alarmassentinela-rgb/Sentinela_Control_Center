"use client";
import { useRouter } from "next/navigation";

import { Card } from "./ui/Card";
import { cn } from "@/lib/cn";
import { formatDate, money } from "@/lib/format";
import type { Invoice } from "@/lib/types";

// `onToggle` activa el modo selección (checkbox) para facturas pendientes.
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
  const label = inv.doc_type === "factura" ? "Factura" : "Remisión";
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
            className="h-5 w-5 shrink-0 accent-[color:var(--brand-primary)]"
            aria-label={`Seleccionar ${inv.number || label}`}
          />
        )}
        <div className="flex min-w-0 flex-1 items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate font-semibold text-ink">{inv.number || label}</p>
            <p className="text-xs text-muted">
              {formatDate(inv.date)} · {label}
            </p>
          </div>
          <div className="text-right">
            <p className="font-semibold text-ink">{money(inv.amount_total, inv.currency)}</p>
            <p className={cn("text-xs", paid ? "text-ok" : "text-warn")}>
              {paid ? "Pagada" : `${money(inv.amount_due, inv.currency)} por pagar`}
            </p>
          </div>
        </div>
      </div>
    </Card>
  );
}
