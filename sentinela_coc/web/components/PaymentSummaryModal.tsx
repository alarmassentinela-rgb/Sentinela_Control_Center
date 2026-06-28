"use client";
import { Button } from "./ui/Button";
import { Dialog } from "./ui/Dialog";
import { formatDate, money } from "@/lib/format";
import type { Invoice } from "@/lib/types";

// Resumen de pago sobre el Dialog ÚNICO del DS. Aquí se abrirá la pasarela en Fase 2; por
// eso el resumen vive dentro de Facturación. (Solo experiencia; sin cobro real todavía.)
export function PaymentSummaryModal({
  open,
  invoices,
  total,
  currency,
  onClose,
}: {
  open: boolean;
  invoices: Invoice[];
  total: number;
  currency: string;
  onClose: () => void;
}) {
  return (
    <Dialog open={open} onClose={onClose} title="Resumen de pago">
      <div className="space-y-2">
        {invoices.map((i) => (
          <div key={i.id} className="flex items-center justify-between gap-3 border-b border-slate-100 pb-2 text-aux">
            <div className="min-w-0">
              <p className="truncate font-medium text-ink">{i.number || "Factura"}</p>
              <p className="text-caption text-muted">Vence {formatDate(i.due_date)}</p>
            </div>
            <p className="whitespace-nowrap font-medium text-ink">{money(i.amount_due, i.currency)}</p>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between py-3 text-subtitle font-bold text-ink">
        <span>Total a pagar</span>
        <span>{money(total, currency)}</span>
      </div>

      <div className="rounded-control bg-amber-50 p-3 text-aux text-amber-800">
        El pago en línea estará disponible próximamente.
      </div>

      <Button className="mt-3 w-full" disabled>
        Pagar (próximamente)
      </Button>
    </Dialog>
  );
}
