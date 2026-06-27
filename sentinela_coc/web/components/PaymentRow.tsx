"use client";
import { Card } from "./ui/Card";
import { formatDate, money } from "@/lib/format";
import type { Payment } from "@/lib/types";

// Fila de pago recibido. Reutiliza Card + formatos; consistente con InvoiceRow.
export function PaymentRow({ p }: { p: Payment }) {
  return (
    <Card>
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-semibold text-ink">{p.reference || "Pago recibido"}</p>
          <p className="text-xs text-muted">{formatDate(p.date)}</p>
        </div>
        <p className="whitespace-nowrap font-semibold text-ok">{money(p.amount, p.currency)}</p>
      </div>
    </Card>
  );
}
