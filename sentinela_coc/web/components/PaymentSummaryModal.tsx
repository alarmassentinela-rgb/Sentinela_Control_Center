"use client";
import { Button } from "./ui/Button";
import { formatDate, money } from "@/lib/format";
import type { Invoice } from "@/lib/types";

// Resumen de pago como panel/modal (NO navega a otra pantalla). Aquí se abrirá la
// pasarela en Fase 2; por eso el resumen vive dentro de Facturación.
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
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-30 flex items-end justify-center bg-black/40 sm:items-center" onClick={onClose}>
      <div
        className="max-h-[85vh] w-full max-w-app overflow-auto rounded-t-xl2 bg-white p-4 sm:rounded-xl2"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
      >
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-bold text-ink">Resumen de pago</h2>
          <button onClick={onClose} className="px-2 text-muted" aria-label="Cerrar">✕</button>
        </div>

        <div className="space-y-2">
          {invoices.map((i) => (
            <div key={i.id} className="flex items-center justify-between gap-3 border-b border-slate-100 pb-2 text-sm">
              <div className="min-w-0">
                <p className="truncate font-medium text-ink">{i.number || "Factura"}</p>
                <p className="text-xs text-muted">Vence {formatDate(i.due_date)}</p>
              </div>
              <p className="whitespace-nowrap font-medium text-ink">{money(i.amount_due, i.currency)}</p>
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between py-3 text-base font-bold text-ink">
          <span>Total a pagar</span>
          <span>{money(total, currency)}</span>
        </div>

        <div className="rounded-lg bg-amber-50 p-3 text-sm text-amber-800">
          El pago en línea estará disponible próximamente.
        </div>

        <Button className="mt-3 w-full" disabled>
          Pagar (próximamente)
        </Button>
      </div>
    </div>
  );
}
