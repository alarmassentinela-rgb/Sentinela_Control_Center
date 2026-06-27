"use client";
import { InvoiceRow } from "@/components/InvoiceRow";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton, SkeletonCard } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { useQuery } from "@/hooks/useQuery";
import { apiGet } from "@/lib/api";
import { money } from "@/lib/format";
import type { BillingSummary, Invoice, Paged } from "@/lib/types";

export default function FacturacionPage() {
  const sum = useQuery(() => apiGet<BillingSummary>("/v1/billing/summary"), []);
  const list = useQuery(() => apiGet<Paged<Invoice>>("/v1/billing/invoices?limit=50"), []);

  return (
    <div className="space-y-3 px-4 pb-4">
      <PageHeader title="Facturación" />

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

      <h2 className="px-1 text-sm font-semibold text-muted">Historial</h2>
      {list.loading && (
        <>
          <SkeletonCard />
          <SkeletonCard />
        </>
      )}
      {list.error && <ErrorState message={list.error} onRetry={list.reload} />}
      {list.data &&
        (list.data.items.length ? (
          list.data.items.map((inv) => <InvoiceRow key={inv.id} inv={inv} />)
        ) : (
          <EmptyState icon="🧾" title="Sin facturas todavía" />
        ))}
    </div>
  );
}
