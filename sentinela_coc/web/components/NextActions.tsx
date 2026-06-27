"use client";
import { useRouter } from "next/navigation";

import { Card } from "./ui/Card";
import { cn } from "@/lib/cn";
import type { NextAction } from "@/lib/types";

const SEV: Record<string, string> = {
  high: "border-l-danger",
  medium: "border-l-warn",
  low: "border-l-slate-300",
};
const ICON: Record<string, string> = {
  payment_overdue: "💸",
  invoice_due: "🧾",
  contract_pending_signature: "✍️",
  service_suspended: "⛔",
};

export function NextActions({ actions }: { actions: NextAction[] }) {
  const router = useRouter();
  if (!actions?.length) return null;
  return (
    <section className="space-y-2">
      <h2 className="px-1 text-sm font-semibold text-muted">Próximas acciones</h2>
      {actions.map((a) => (
        <Card key={a.key} onClick={() => router.push(a.target)} className={cn("border-l-4", SEV[a.severity] || SEV.low)}>
          <div className="flex items-start gap-3">
            <div className="text-xl" aria-hidden>{ICON[a.type] || "•"}</div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold text-ink">{a.title}</p>
              <p className="text-xs text-muted">{a.detail}</p>
            </div>
            <div className="text-slate-300">›</div>
          </div>
        </Card>
      ))}
    </section>
  );
}
