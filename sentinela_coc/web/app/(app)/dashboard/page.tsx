"use client";
import Link from "next/link";

import { ModulesGrid } from "@/components/ModulesGrid";
import { NextActions } from "@/components/NextActions";
import { PeaceOfMind } from "@/components/PeaceOfMind";
import { ServiceCard } from "@/components/ServiceCard";
import { Badge } from "@/components/ui/Badge";
import { Card } from "@/components/ui/Card";
import { Skeleton, SkeletonCard } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import { useQuery } from "@/hooks/useQuery";
import { accountStatus } from "@/lib/accountState";
import { apiGetEnvelope } from "@/lib/api";
import { money } from "@/lib/format";
import type { Dashboard } from "@/lib/types";

export default function DashboardPage() {
  const { data, loading, error, reload } = useQuery(() => apiGetEnvelope<Dashboard>("/v1/dashboard"), []);

  return (
    <div className="space-y-4 px-4 pb-4 pt-4">
      {loading && (
        <>
          <Skeleton className="h-36 w-full rounded-card" />
          <SkeletonCard />
          <SkeletonCard />
        </>
      )}

      {error && <ErrorState message={error} onRetry={reload} />}

      {data && (
        // Dos COLUMNAS INDEPENDIENTES en escritorio (sin acoplamiento de filas, evita
        // huecos/orfandad): principal (hero protagonista + Próximas acciones) y lateral
        // (Saldo + Servicios + Módulos apilados). En móvil se apila en una columna.
        <div className="space-y-4 lg:grid lg:grid-cols-3 lg:gap-4 lg:space-y-0 lg:items-start">
          {/* Columna principal (2/3) */}
          <div className="space-y-4 lg:col-span-2">
            <PeaceOfMind status={accountStatus(data.data)} />
            {data.data.next_actions.length > 0 && <NextActions actions={data.data.next_actions} />}
          </div>

          {/* Columna lateral (1/3) */}
          <div className="space-y-4">
            <Card className="flex items-center justify-between">
              <div>
                <p className="text-caption text-muted">Saldo por pagar</p>
                <p className="text-subtitle font-bold text-ink">{money(data.data.billing.total_due, data.data.billing.currency)}</p>
              </div>
              {data.data.billing.overdue_amount > 0 && (
                <Badge tone="danger">Vencido {money(data.data.billing.overdue_amount, data.data.billing.currency)}</Badge>
              )}
            </Card>

            <section className="space-y-2">
              <h2 className="px-1 text-aux font-semibold text-muted">Mis servicios</h2>
              {data.data.services.items.length ? (
                <>
                  {data.data.services.items.slice(0, 3).map((s) => <ServiceCard key={s.id} s={s} />)}
                  {data.data.services.total > 3 && (
                    <Link
                      href="/servicios"
                      className="focus-ring block rounded-control border border-slate-200 bg-surface py-2 text-center text-aux font-semibold text-brand"
                    >
                      Ver todos los servicios ({data.data.services.total})
                    </Link>
                  )}
                </>
              ) : (
                <p className="px-1 text-aux text-muted">Aún no tienes servicios.</p>
              )}
            </section>

            <ModulesGrid />
          </div>

          {data.meta.last_refresh && (
            <p className="px-1 text-center text-caption text-muted lg:col-span-3">
              Actualizado {new Date(data.meta.last_refresh).toLocaleTimeString("es-MX")}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
