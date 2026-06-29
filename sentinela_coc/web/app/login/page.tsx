"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { BrandMark } from "@/components/BrandMark";
import { Button } from "@/components/ui/Button";
import { FieldLabel } from "@/components/ui/FieldLabel";
import { apiPostPublic } from "@/lib/api";
import { getDeviceId, setTokens, type Tokens } from "@/lib/auth";
import { authVerifyError, friendlyError } from "@/lib/format";

export default function LoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  // El aviso de expiración aparece SOLO cuando se llega por sesión expirada (?expired=1),
  // nunca en una entrada normal al portal.
  const [expired, setExpired] = useState(false);
  useEffect(() => {
    setExpired(new URLSearchParams(window.location.search).get("expired") === "1");
  }, []);

  async function requestOtp(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await apiPostPublic("/v1/auth/otp/request", { phone, device: getDeviceId() });
      setStep("code");
      setInfo("Te enviamos un código por WhatsApp.");
    } catch (err) {
      setError(friendlyError(err));
    } finally {
      setLoading(false);
    }
  }

  async function verifyOtp(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const t = await apiPostPublic<Tokens>("/v1/auth/otp/verify", { phone, code, device: getDeviceId() });
      setTokens(t);
      router.replace("/dashboard");
    } catch (e) {
      setError(authVerifyError(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell relative justify-center px-6">
      <div className="mx-auto w-full max-w-sm space-y-6 pb-16">
        {/* Identidad = BrandMark (única fuente: logo de Odoo + título). */}
        <BrandMark layout="login" />

        {expired && (
          <p className="rounded-control border border-amber-200 bg-amber-50 px-4 py-3 text-center text-aux text-amber-800">
            Tu sesión expiró. Inicia sesión nuevamente para continuar.
          </p>
        )}

        {step === "phone" ? (
          <form onSubmit={requestOtp} className="space-y-3">
            <FieldLabel htmlFor="phone">Tu número de WhatsApp</FieldLabel>
            <input
              id="phone"
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              required
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+52 868 123 4567"
              className="focus-ring w-full rounded-control border border-slate-200 bg-white px-4 py-3 text-base"
            />
            <Button type="submit" className="w-full" disabled={loading || !phone}>
              {loading ? "Enviando…" : "Enviar código"}
            </Button>
          </form>
        ) : (
          <form onSubmit={verifyOtp} className="space-y-3">
            {info && <p className="text-center text-aux text-muted">{info}</p>}
            <FieldLabel htmlFor="code">Código de 6 dígitos</FieldLabel>
            <input
              id="code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              required
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              placeholder="••••••"
              className="focus-ring w-full rounded-control border border-slate-200 bg-white px-4 py-3 text-center text-2xl tracking-[0.5em]"
            />
            <Button type="submit" className="w-full" disabled={loading || code.length < 6}>
              {loading ? "Verificando…" : "Entrar"}
            </Button>
            <Button type="button" variant="ghost" className="w-full" onClick={() => { setStep("phone"); setCode(""); setError(null); }}>
              Usar otro número
            </Button>
          </form>
        )}

        {error && <p className="text-center text-aux text-danger">{error}</p>}
      </div>

      {/* Pie institucional discreto (cosmético, no afecta el centrado ni el login). */}
      <footer className="absolute inset-x-0 bottom-0 space-y-0.5 px-6 pb-5 text-center text-caption text-muted">
        <p>Portal del Cliente v1.0</p>
        <p>© 2026 Alarmas Sentinela</p>
        <p>Powered by Alea Systems</p>
      </footer>
    </main>
  );
}
