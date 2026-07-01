// Stripe.js singleton (S2-014 confirmación en la SPA). La clave PÚBLICA de prueba
// llega por build (NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY, pk_test_...). El PAN nunca toca
// nuestros servidores: Stripe Elements lo captura y confirma con el client_secret.
import { loadStripe, type Stripe } from "@stripe/stripe-js";

let _promise: Promise<Stripe | null> | null = null;

export function getStripe(): Promise<Stripe | null> {
  if (!_promise) {
    const pk = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY;
    _promise = pk ? loadStripe(pk) : Promise.resolve(null);
  }
  return _promise;
}
