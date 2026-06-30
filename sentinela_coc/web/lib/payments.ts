// Pago en línea (S2-014). startPayment() invoca el backend real
// (POST /v1/payments/start): valida contra el Ledger, inicia el cobro vía el Motor de
// Pago y devuelve el estado {confirmado/en proceso/rechazado}. La SPA NO conoce el
// proveedor: solo consume el estado de negocio.
import { ApiError, apiPost } from "./api";
import type { Invoice } from "./types";

export function paymentPreviewTotal(invoices: Invoice[]): number {
  return Math.round(invoices.reduce((s, i) => s + (i.amount_due || 0), 0) * 100) / 100;
}

export function isPayable(inv: Invoice): boolean {
  return inv.payment_state !== "paid" && (inv.amount_due || 0) > 0;
}

export type PaymentStatus = "confirmed" | "processing" | "rejected";

export type PaymentStartResult =
  | {
      ok: true;
      status: PaymentStatus;
      payment_id: string;
      provider_ref: string | null;
      amount: number;
      currency: string;
      client_action: { client_secret?: string } | null;
    }
  | { ok: false; error: string };

type StartResponse = {
  payment_id: string;
  status: PaymentStatus;
  provider_ref: string | null;
  amount: number;
  currency: string;
  client_action: { client_secret?: string } | null;
};

export async function startPayment(invoiceIds: number[], amount: number): Promise<PaymentStartResult> {
  try {
    const d = await apiPost<StartResponse>("/v1/payments/start", { invoice_ids: invoiceIds, amount });
    return {
      ok: true,
      status: d.status,
      payment_id: d.payment_id,
      provider_ref: d.provider_ref,
      amount: d.amount,
      currency: d.currency,
      client_action: d.client_action,
    };
  } catch (e) {
    // 422 = montos/facturas no cuadran con el Ledger (mensaje claro del backend).
    const msg = e instanceof ApiError ? e.message : "No pudimos iniciar el pago. Intenta de nuevo.";
    return { ok: false, error: msg };
  }
}
