"use client";
import { useParams } from "next/navigation";

import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { SkeletonText } from "@/components/ui/Skeleton";
import { StatusPill } from "@/components/ui/StatusPill";
import { ErrorState } from "@/components/ui/States";
import { useQuery } from "@/hooks/useQuery";
import { apiGet } from "@/lib/api";
import { formatDate, money, serviceIcon } from "@/lib/format";
import type { Service } from "@/lib/types";

function Row({ k, v }: { k: string; v?: string | null }) {
  return (
    <div className="flex justify-between gap-4 border-t border-slate-100 pt-2 text-sm">
      <span className="text-muted">{k}</span>
      <span className="text-right font-medium text-ink">{v || "—"}</span>
    </div>
  );
}

export default function ServicioDetallePage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const { data, loading, error, reload } = useQuery(() => apiGet<Service>(`/v1/services/${id}`), [id]);

  return (
    <div className="space-y-3 px-4 pb-4 lg:mx-auto lg:max-w-2xl">
      <PageHeader title="Servicio" />
      {loading && (
        <Card>
          <SkeletonText lines={5} />
        </Card>
      )}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && (
        <Card className="space-y-3">
          <div className="flex items-center gap-3">
            <div className="text-3xl" aria-hidden>{serviceIcon(data.service_type)}</div>
            <div className="flex-1">
              <p className="font-bold text-ink">{data.service_type_label}</p>
              <p className="text-xs text-muted">{data.reference}</p>
            </div>
            <StatusPill status={data.status} />
          </div>
          <Row k="Plan" v={data.plan} />
          <Row k="Tarifa" v={`${money(data.monthly_total, data.currency)} / ${data.billing_interval_label}`} />
          <Row k="Próximo cobro" v={formatDate(data.next_billing_date)} />
          <Row k="Domicilio" v={data.service_address} />
        </Card>
      )}
    </div>
  );
}
