"use client";
import { useEffect, useState } from "react";

import { InvoiceRow } from "@/components/InvoiceRow";
import { PaymentRow } from "@/components/PaymentRow";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton, SkeletonCard } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { useQuery } from "@/hooks/useQuery";
import { apiGet } from "@/lib/api";
import { cn } from "@/lib/cn";
import { money } from "@/lib/format";
import type { BillingSummary, Invoice, Paged, Payment } from "@/lib/types";

type Tab = "facturas" | "pagos";
const TAB_KEY = "fact.tab";

export default function FacturacionPage() {
  const sum = useQuery(() => apiGet<BillingSummary>("/v1/billing/summary"), []);
  const list = useQuery(() => apiGet<Paged<Invoice>>("/v1/billing/invoices?limit=50"), []);
  const pays = useQuery(() => apiGet<Paged<Payment>>("/v1/billing/payments?limit=50"), []);

  // Pestaña persistida (se conserva al alternar y al volver del detalle de una factura).
  const [tab, setTab] = useState<Tab>("facturas");
  useEffect(() => {
    const t = sessionStorage.getItem(TAB_KEY);
    if (t === "pagos" || t === "facturas") setTab(t);
  }, []);
  function changeTab(t: Tab) {
    setTab(t);
    sessionStorage.setItem(TAB_KEY, t);
  }

  return (
    <div className="space-y-3 px-4 pb-4">
      <PageHeader title="Facturación" />

      {/* Resumen SIEMPRE visible */}
      {sum.loading ? (
        <Skeleton className="h-24 w-full rounded-xl2" />
      ) : sum.error ? (
        <ErrorState message={sum.error} onRetry={sum.reload} />
      ) : (
        sum.data && (
          <Card className="flex items-center justify-between">
            <div>
              <p className="text-xs text-muted">Saldo por pagar</p>
              <p className="text-xl font-bold text-ink">{money(sum.data.total_due, sum.data.currency)}</p>
            </div>
            {sum.data.overdue_amount > 0 && (
              <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-700">
                Vencido {money(sum.data.overdue_amount, sum.data.currency)}
              </span>
            )}
          </Card>
        )
      )}

      {/* Selector Facturas | Pagos — solo cambia el contenido inferior */}
      <div className="inline-flex rounded-xl bg-slate-100 p-1 text-sm font-semibold">
        {(["facturas", "pagos"] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => changeTab(t)}
            className={cn(
              "rounded-lg px-4 py-1.5 capitalize transition",
              tab === t ? "bg-white text-ink shadow-sm" : "text-muted",
            )}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "facturas" ? (
        <>
          {list.loading && (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <SkeletonCard />
              <SkeletonCard />
            </div>
          )}
          {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
          {list.data &&
            (list.data.items.length ? (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {list.data.items.map((inv) => <InvoiceRow key={inv.id} inv={inv} />)}
              </div>
            ) : (
              <EmptyState icon="🧾" title="Sin facturas todavía" />
            ))}
        </>
      ) : (
        <>
          {pays.loading && (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <SkeletonCard />
              <SkeletonCard />
            </div>
          )}
          {pays.error && <ErrorState message={pays.error} onRetry={pays.reload} />}
          {pays.data &&
            (pays.data.items.length ? (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {pays.data.items.map((p) => <PaymentRow key={p.id} p={p} />)}
              </div>
            ) : (
              <EmptyState icon="💳" title="Aún no tienes pagos registrados" />
            ))}
        </>
      )}
    </div>
  );
}
