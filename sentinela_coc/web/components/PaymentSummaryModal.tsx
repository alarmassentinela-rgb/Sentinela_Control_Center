"use client";
import { useState } from "react";

import { Button } from "./ui/Button";
import { Dialog } from "./ui/Dialog";
import { formatDate, money } from "@/lib/format";
import { startPayment, type PaymentStatus } from "@/lib/payments";
import type { Invoice } from "@/lib/types";

// Resumen + pago en línea (S2-014). Invoca startPayment() real y maneja los 3 estados
// del negocio. La SPA no conoce el proveedor: solo muestra confirmado/en proceso/rechazado.
type View =
  | { kind: "summary" }
  | { kind: "loading" }
  | { kind: "result"; status: PaymentStatus }
  | { kind: "error"; message: string };

const RESULT_UX: Record<PaymentStatus, { tone: string; title: string; detail: string }> = {
  confirmed: {
    tone: "border-emerald-200 bg-emerald-50 text-emerald-800",
    title: "¡Pago confirmado!",
    detail: "Tu estado de cuenta ya está actualizado.",
  },
  processing: {
    tone: "border-amber-200 bg-amber-50 text-amber-800",
    title: "Pago en proceso",
    detail: "Estamos confirmando tu pago. Te avisaremos en cuanto se complete.",
  },
  rejected: {
    tone: "border-red-200 bg-red-50 text-red-700",
    title: "Pago rechazado",
    detail: "No se pudo procesar el pago. Verifica tu método e intenta de nuevo.",
  },
};

export function PaymentSummaryModal({
  open,
  invoices,
  total,
  currency,
  onClose,
  onPaid,
}: {
  open: boolean;
  invoices: Invoice[];
  total: number;
  currency: string;
  onClose: () => void;
  onPaid?: () => void;
}) {
  const [view, setView] = useState<View>({ kind: "summary" });
  // Congela las facturas/total al momento de pagar: así el resultado muestra el monto
  // estable aunque el padre refresque/limpie la selección tras onPaid().
  const [snap, setSnap] = useState<{ invoices: Invoice[]; total: number } | null>(null);
  const shownInvoices = snap?.invoices ?? invoices;
  const shownTotal = snap?.total ?? total;

  function close() {
    setView({ kind: "summary" });
    setSnap(null);
    onClose();
  }

  async function pay() {
    setSnap({ invoices, total });
    setView({ kind: "loading" });
    const res = await startPayment(invoices.map((i) => i.id), total);
    if (!res.ok) {
      setView({ kind: "error", message: res.error });
      return;
    }
    setView({ kind: "result", status: res.status });
    // Confirmado o en proceso: el Estado de Cuenta (Ledger) puede haber cambiado.
    if (res.status !== "rejected") onPaid?.();
  }

  return (
    <Dialog open={open} onClose={close} title="Resumen de pago">
      <div className="space-y-2">
        {shownInvoices.map((i) => (
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
        <span>{money(shownTotal, currency)}</span>
      </div>

      {view.kind === "result" && (
        <div className={`rounded-control border p-3 text-aux ${RESULT_UX[view.status].tone}`} role="status">
          <p className="font-semibold">{RESULT_UX[view.status].title}</p>
          <p>{RESULT_UX[view.status].detail}</p>
        </div>
      )}
      {view.kind === "error" && (
        <p className="rounded-control border border-red-200 bg-red-50 p-3 text-aux text-red-700" role="alert">
          {view.message}
        </p>
      )}

      {view.kind === "result" && view.status !== "rejected" ? (
        <Button className="mt-3 w-full" onClick={close}>
          Listo
        </Button>
      ) : (
        <Button className="mt-3 w-full" onClick={pay} disabled={view.kind === "loading"}>
          {view.kind === "loading"
            ? "Procesando…"
            : view.kind === "result" || view.kind === "error"
              ? "Reintentar"
              : `Pagar ${money(shownTotal, currency)}`}
        </Button>
      )}
    </Dialog>
  );
}
