"use client";
import { ModulesGrid } from "@/components/ModulesGrid";
import { NextActions } from "@/components/NextActions";
import { PeaceOfMind } from "@/components/PeaceOfMind";
import { ServiceCard } from "@/components/ServiceCard";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { Skeleton, SkeletonCard } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import { useQuery } from "@/hooks/useQuery";
import { apiGetEnvelope } from "@/lib/api";
import { money } from "@/lib/format";
import type { Dashboard } from "@/lib/types";

export default function DashboardPage() {
  const { data, loading, error, reload } = useQuery(() => apiGetEnvelope<Dashboard>("/v1/dashboard"), []);

  return (
    <div className="space-y-4 px-4 pb-4">
      <PageHeader title="Hola 👋" subtitle="Tu Centro de Operaciones" />

      {loading && (
        <>
          <Skeleton className="h-36 w-full rounded-xl2" />
          <SkeletonCard />
          <SkeletonCard />
        </>
      )}

      {error && <ErrorState message={error} onRetry={reload} />}

      {data && (
        <>
          <PeaceOfMind status={data.data.peace_of_mind.status} label={data.data.peace_of_mind.label} />

          <Card className="flex items-center justify-between">
            <div>
              <p className="text-xs text-muted">Saldo por pagar</p>
              <p className="text-lg font-bold text-ink">{money(data.data.billing.total_due, data.data.billing.currency)}</p>
            </div>
            {data.data.billing.overdue_amount > 0 && (
              <span className="rounded-full bg-red-100 px-3 py-1 text-xs font-semibold text-red-700">
                Vencido {money(data.data.billing.overdue_amount, data.data.billing.currency)}
              </span>
            )}
          </Card>

          <NextActions actions={data.data.next_actions} />

          <section className="space-y-2">
            <h2 className="px-1 text-sm font-semibold text-muted">Mis servicios</h2>
            {data.data.services.items.length ? (
              data.data.services.items.map((s) => <ServiceCard key={s.id} s={s} />)
            ) : (
              <p className="px-1 text-sm text-muted">Aún no tienes servicios.</p>
            )}
          </section>

          <ModulesGrid />

          {data.meta.last_refresh && (
            <p className="px-1 text-center text-[10px] text-slate-400">
              Actualizado {new Date(data.meta.last_refresh).toLocaleTimeString("es-MX")}
            </p>
          )}
        </>
      )}
    </div>
  );
}
