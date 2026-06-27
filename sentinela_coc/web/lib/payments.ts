// Costura de pagos (Fase 2). HOY no procesa cobro: solo prepara la experiencia.
// Cuando se integre la pasarela, SOLO se implementa startPayment() para llamar a
// POST /v1/billing/payment-intent (total recalculado server-side) — la UX no cambia.
import type { Invoice } from "./types";

export function paymentPreviewTotal(invoices: Invoice[]): number {
  return Math.round(invoices.reduce((s, i) => s + (i.amount_due || 0), 0) * 100) / 100;
}

export function isPayable(inv: Invoice): boolean {
  return inv.payment_state !== "paid" && (inv.amount_due || 0) > 0;
}

export type PaymentStart = { status: "not_available" | "ok"; reference?: string; message?: string };

export async function startPayment(_invoiceIds: number[]): Promise<PaymentStart> {
  // Fase 2: aquí se invocará el gateway + pasarela. Por ahora, no disponible.
  return { status: "not_available", message: "El pago en línea estará disponible próximamente." };
}
