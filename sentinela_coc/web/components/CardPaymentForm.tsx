"use client";
import { useState } from "react";
import { Elements, PaymentElement, useElements, useStripe } from "@stripe/react-stripe-js";

import { Button } from "./ui/Button";
import { money } from "@/lib/format";
import { getStripe } from "@/lib/stripe";
import type { PaymentStatus } from "@/lib/payments";

// Confirmación del pago EN PÁGINA (S2-014): el cliente ingresa la tarjeta en Stripe
// Elements y confirma el PaymentIntent con el client_secret que ya entrega el Gateway.
// 3DS se resuelve in-page (redirect: "if_required" + allow_redirects: "never" en el PI).
function mapStatus(s?: string): PaymentStatus {
  if (s === "succeeded") return "confirmed";
  if (s === "processing") return "processing";
  return "rejected";
}

function Inner({
  amount,
  currency,
  onResult,
}: {
  amount: number;
  currency: string;
  onResult: (s: PaymentStatus) => void;
}) {
  const stripe = useStripe();
  const elements = useElements();
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!stripe || !elements) return;
    setBusy(true);
    setErr(null);
    const { error, paymentIntent } = await stripe.confirmPayment({
      elements,
      redirect: "if_required",
    });
    if (error) {
      // Error de tarjeta/validación: no se aplicó el pago; se permite reintento.
      setErr(error.message || "No se pudo procesar el pago. Verifica tu tarjeta e intenta de nuevo.");
      setBusy(false);
      return;
    }
    onResult(mapStatus(paymentIntent?.status));
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <PaymentElement options={{ layout: "tabs" }} />
      {err && (
        <p className="rounded-control border border-red-200 bg-red-50 p-3 text-aux text-red-700" role="alert">
          {err}
        </p>
      )}
      <Button type="submit" className="w-full" disabled={!stripe || busy}>
        {busy ? "Procesando…" : `Pagar ${money(amount, currency)}`}
      </Button>
    </form>
  );
}

export function CardPaymentForm({
  clientSecret,
  amount,
  currency,
  onResult,
}: {
  clientSecret: string;
  amount: number;
  currency: string;
  onResult: (s: PaymentStatus) => void;
}) {
  return (
    <Elements stripe={getStripe()} options={{ clientSecret, appearance: { theme: "stripe" } }}>
      <Inner amount={amount} currency={currency} onResult={onResult} />
    </Elements>
  );
}
