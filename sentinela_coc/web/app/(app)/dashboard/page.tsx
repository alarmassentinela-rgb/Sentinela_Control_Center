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
        // Jerarquía: el Estado de Tranquilidad (hero) ocupa la columna ancha (8/12);
        // los paneles secundarios van a 4/12. En móvil se apila igual que antes.
        <div className="space-y-4 lg:grid lg:grid-cols-12 lg:gap-4 lg:space-y-0 lg:items-start">
          <div className="lg:col-span-8">
            <PeaceOfMind status={data.data.peace_of_mind.status} label={data.data.peace_of_mind.label} />
          </div>

          <Card className="flex items-center justify-between lg:col-span-4">
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

          {data.data.next_actions.length > 0 && (
            <div className="lg:col-span-4">
              <NextActions actions={data.data.next_actions} />
            </div>
          )}

          <section className="space-y-2 lg:col-span-4">
            <h2 className="px-1 text-sm font-semibold text-muted">Mis servicios</h2>
            {data.data.services.items.length ? (
              data.data.services.items.map((s) => <ServiceCard key={s.id} s={s} />)
            ) : (
              <p className="px-1 text-sm text-muted">Aún no tienes servicios.</p>
            )}
          </section>

          <div className="lg:col-span-4">
            <ModulesGrid />
          </div>

          {data.meta.last_refresh && (
            <p className="px-1 text-center text-[10px] text-slate-400 lg:col-span-12">
              Actualizado {new Date(data.meta.last_refresh).toLocaleTimeString("es-MX")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
