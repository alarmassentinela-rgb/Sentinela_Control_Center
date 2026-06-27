"use client";
import { useEffect, useMemo, useState } from "react";

import { InvoiceRow } from "@/components/InvoiceRow";
import { PaymentRow } from "@/components/PaymentRow";
import { PaymentSummaryModal } from "@/components/PaymentSummaryModal";
import { SelectionBar } from "@/components/SelectionBar";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton, SkeletonCard } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { useQuery } from "@/hooks/useQuery";
import { apiGet } from "@/lib/api";
import { cn } from "@/lib/cn";
import { formatDate, money } from "@/lib/format";
import { paymentPreviewTotal } from "@/lib/payments";
import type { BillingSummary, Invoice, Paged, Payment } from "@/lib/types";

type Tab = "facturas" | "pagos";
const TAB_KEY = "fact.tab";

function Metric({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "danger" }) {
  return (
    <div>
      <p className="text-[11px] text-muted">{label}</p>
      <p className={cn("text-base font-bold", tone === "danger" ? "text-danger" : "text-ink")}>{value}</p>
      {sub && <p className="text-[10px] text-muted">{sub}</p>}
    </div>
  );
}

export default function FacturacionPage() {
  const sum = useQuery(() => apiGet<BillingSummary>("/v1/billing/summary"), []);
  const list = useQuery(() => apiGet<Paged<Invoice>>("/v1/billing/invoices?limit=50"), []);
  const pays = useQuery(() => apiGet<Paged<Payment>>("/v1/billing/payments?limit=50"), []);

  const [tab, setTab] = useState<Tab>("facturas");
  useEffect(() => {
    const t = sessionStorage.getItem(TAB_KEY);
    if (t === "pagos" || t === "facturas") setTab(t);
  }, []);
  function changeTab(t: Tab) {
    setTab(t);
    sessionStorage.setItem(TAB_KEY, t);
  }

  // Selección de facturas a pagar (experiencia completa; el cobro llega en Fase 2)
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [showSummary, setShowSummary] = useState(false);
  function toggle(id: number) {
    setSelected((prev) => {
      const n = new Set(prev);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  }

  const invoices = list.data?.items || [];
  const selectedInvoices = useMemo(() => invoices.filter((i) => selected.has(i.id)), [invoices, selected]);
  const total = paymentPreviewTotal(selectedInvoices);
  const currency = sum.data?.currency || "MXN";
  const latestPayment = pays.data?.items?.[0];
  const nextDue = sum.data?.upcoming?.[0]?.due_date;

  return (
    <div className="space-y-3 px-4 pb-24">
      <PageHeader title="Facturación" />

      {/* Resumen ejecutivo (situación financiera de un vistazo) */}
      {sum.loading ? (
        <Skeleton className="h-24 w-full rounded-xl2" />
      ) : sum.error ? (
        <ErrorState message={sum.error} onRetry={sum.reload} />
      ) : (
        sum.data && (
          <Card>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Metric label="Facturas pendientes" value={String(sum.data.open_count)} />
              <Metric
                label="Importe pendiente"
                value={money(sum.data.total_due, currency)}
                tone={sum.data.overdue_amount > 0 ? "danger" : undefined}
              />
              <Metric label="Próximo vencimiento" value={nextDue ? formatDate(nextDue) : "—"} />
              <Metric
                label="Último pago"
                value={latestPayment ? money(latestPayment.amount, latestPayment.currency) : "—"}
                sub={latestPayment ? formatDate(latestPayment.date) : undefined}
              />
            </div>
          </Card>
        )
      )}

      {/* Selector Facturas | Pagos */}
      <div className="inline-flex rounded-xl bg-slate-100 p-1 text-sm font-semibold">
        {(["facturas", "pagos"] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => changeTab(t)}
            className={cn("rounded-lg px-4 py-1.5 capitalize transition", tab === t ? "bg-white text-ink shadow-sm" : "text-muted")}
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
            (invoices.length ? (
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {invoices.map((inv) => (
                  <InvoiceRow key={inv.id} inv={inv} selected={selected.has(inv.id)} onToggle={toggle} />
                ))}
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

      {tab === "facturas" && (
        <SelectionBar count={selectedInvoices.length} total={total} currency={currency} onContinue={() => setShowSummary(true)} />
      )}
      <PaymentSummaryModal
        open={showSummary}
        invoices={selectedInvoices}
        total={total}
        currency={currency}
        onClose={() => setShowSummary(false)}
      />
    </div>
  );
}
