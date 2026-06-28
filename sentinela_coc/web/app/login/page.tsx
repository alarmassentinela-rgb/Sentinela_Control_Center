"use client";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { BrandMark } from "@/components/BrandMark";
import { Button } from "@/components/ui/Button";
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
    <main className="app-shell justify-center px-6">
      <div className="mx-auto w-full max-w-sm space-y-6 pb-16">
        {/* Identidad = BrandMark (única fuente: logo de Odoo + título). */}
        <BrandMark layout="login" />

        {step === "phone" ? (
          <form onSubmit={requestOtp} className="space-y-3">
            <label className="block text-sm font-medium text-ink">Tu número de WhatsApp</label>
            <input
              type="tel"
              inputMode="tel"
              autoComplete="tel"
              required
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+52 868 123 4567"
              className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-base outline-none focus:border-brand"
            />
            <Button type="submit" className="w-full" disabled={loading || !phone}>
              {loading ? "Enviando…" : "Enviar código"}
            </Button>
          </form>
        ) : (
          <form onSubmit={verifyOtp} className="space-y-3">
            {info && <p className="text-center text-sm text-muted">{info}</p>}
            <label className="block text-sm font-medium text-ink">Código de 6 dígitos</label>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              required
              value={code}
              onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
              placeholder="••••••"
              className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-center text-2xl tracking-[0.5em] outline-none focus:border-brand"
            />
            <Button type="submit" className="w-full" disabled={loading || code.length < 6}>
              {loading ? "Verificando…" : "Entrar"}
            </Button>
            <Button type="button" variant="ghost" className="w-full" onClick={() => { setStep("phone"); setCode(""); setError(null); }}>
              Usar otro número
            </Button>
          </form>
        )}

        {error && <p className="text-center text-sm text-danger">{error}</p>}
      </div>
    </main>
  );
}
