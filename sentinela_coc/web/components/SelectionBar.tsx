"use client";
import { Button } from "./ui/Button";
import { money } from "@/lib/format";

// Barra fija inferior (flota sobre el BottomNav) con el total seleccionado + "Continuar".
export function SelectionBar({
  count,
  total,
  currency,
  onContinue,
}: {
  count: number;
  total: number;
  currency: string;
  onContinue: () => void;
}) {
  if (count <= 0) return null;
  return (
    <div className="fixed inset-x-0 bottom-[64px] z-overlay px-4">
      <div className="mx-auto flex max-w-app items-center justify-between gap-3 rounded-card border border-slate-200 bg-surface px-4 py-3 shadow-overlay md:max-w-3xl lg:max-w-5xl xl:max-w-desktop">
        <div>
          <p className="text-caption text-muted">{count} factura(s) seleccionada(s) · Total</p>
          <p className="text-subtitle font-bold text-ink">{money(total, currency)}</p>
        </div>
        <Button onClick={onContinue}>Continuar</Button>
      </div>
    </div>
  );
}
