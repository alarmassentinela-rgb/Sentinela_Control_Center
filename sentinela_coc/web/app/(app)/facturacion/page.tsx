"use client";
import { useEffect, useMemo, useState } from "react";

import { InvoiceRow } from "@/components/InvoiceRow";
import { PaymentRow } from "@/components/PaymentRow";
import { PaymentSummaryModal } from "@/components/PaymentSummaryModal";
import { SelectionBar } from "@/components/SelectionBar";
import { Card } from "@/components/ui/Card";
import { LoadMore } from "@/components/ui/LoadMore";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton, SkeletonCard } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { usePaged } from "@/hooks/usePaged";
import { useQuery } from "@/hooks/useQuery";
import { apiGet } from "@/lib/api";
import { cn } from "@/lib/cn";
import { formatDate, money } from "@/lib/format";
import { paymentPreviewTotal } from "@/lib/payments";
import type { AccountStatement, Invoice, Payment } from "@/lib/types";

type Tab = "facturas" | "pagos";
const TAB_KEY = "fact.tab";

function Metric({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "danger" }) {
  return (
    <div>
      <p className="text-caption text-muted">{label}</p>
      <p className={cn("text-body font-bold", tone === "danger" ? "text-danger" : "text-ink")}>{value}</p>
      {sub && <p className="text-caption text-muted">{sub}</p>}
    </div>
  );
}

export default function FacturacionPage() {
  // Estado de Cuenta desde el Ledger (única fuente del saldo/vencido/por vencer).
  const sum = useQuery(() => apiGet<AccountStatement>("/v1/ledger/statement"), []);
  const inv = usePaged<Invoice>("/v1/billing/invoices", {}, 20);
  const pays = usePaged<Payment>("/v1/billing/payments", {}, 20);

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

  const invoices = inv.items;
  const selectedInvoices = useMemo(() => invoices.filter((i) => selected.has(i.id)), [invoices, selected]);
  const total = paymentPreviewTotal(selectedInvoices);
  const currency = sum.data?.currency || "MXN";
  const latestPayment = pays.items[0];

  return (
    <div className="space-y-3 px-4 pb-24">
      <PageHeader title="Facturación" />

      {/* Resumen ejecutivo (situación financiera de un vistazo) */}
      {sum.loading ? (
        <Skeleton className="h-24 w-full rounded-card" />
      ) : sum.error ? (
        <ErrorState message={sum.error} onRetry={sum.reload} />
      ) : (
        sum.data && (
          <Card>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <Metric
                label="Saldo por pagar"
                value={money(sum.data.balance, currency)}
                tone={sum.data.overdue > 0 ? "danger" : undefined}
              />
              <Metric
                label="Vencido"
                value={money(sum.data.overdue, currency)}
                tone={sum.data.overdue > 0 ? "danger" : undefined}
              />
              <Metric label="Por vencer" value={money(sum.data.upcoming, currency)} />
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
      <div className="inline-flex rounded-control bg-slate-100 p-1 text-aux font-semibold">
        {(["facturas", "pagos"] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => changeTab(t)}
            className={cn("focus-ring rounded-control px-4 py-1.5 capitalize transition", tab === t ? "bg-white text-ink shadow-card" : "text-muted")}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "facturas" ? (
        <>
          {inv.error && <ErrorState message={inv.error} onRetry={inv.reload} />}
          {inv.loading && invoices.length === 0 && (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <SkeletonCard />
              <SkeletonCard />
            </div>
          )}
          {!inv.loading && !inv.error && invoices.length === 0 && <EmptyState icon="🧾" title="Sin facturas todavía" />}
          {invoices.length > 0 && (
            <>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {invoices.map((i) => (
                  <InvoiceRow key={i.id} inv={i} selected={selected.has(i.id)} onToggle={toggle} />
                ))}
              </div>
              <LoadMore shown={invoices.length} total={inv.total} loading={inv.loading} onMore={inv.loadMore} />
            </>
          )}
        </>
      ) : (
        <>
          {pays.error && <ErrorState message={pays.error} onRetry={pays.reload} />}
          {pays.loading && pays.items.length === 0 && (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              <SkeletonCard />
              <SkeletonCard />
            </div>
          )}
          {!pays.loading && !pays.error && pays.items.length === 0 && (
            <EmptyState icon="💳" title="Aún no tienes pagos registrados" />
          )}
          {pays.items.length > 0 && (
            <>
              <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {pays.items.map((p) => <PaymentRow key={p.id} p={p} />)}
              </div>
              <LoadMore shown={pays.items.length} total={pays.total} loading={pays.loading} onMore={pays.loadMore} />
            </>
          )}
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
        onPaid={() => {
          setSelected(new Set());
          sum.reload();
          inv.reload();
          pays.reload();
        }}
      />
    </div>
  );
}
