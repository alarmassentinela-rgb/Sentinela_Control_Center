"use client";
import { ServiceCard } from "@/components/ServiceCard";
import { PageHeader } from "@/components/ui/PageHeader";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { EmptyState, ErrorState } from "@/components/ui/States";
import { useQuery } from "@/hooks/useQuery";
import { apiGet } from "@/lib/api";
import type { Service } from "@/lib/types";

export default function ServiciosPage() {
  const { data, loading, error, reload } = useQuery(
    () => apiGet<{ items: Service[]; count: number }>("/v1/services"),
    [],
  );

  return (
    <div className="px-4 pb-4">
      <PageHeader title="Mis Servicios" />
      {error && <ErrorState message={error} onRetry={reload} />}
      {loading && (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}
      {data &&
        (data.items.length ? (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {data.items.map((s) => <ServiceCard key={s.id} s={s} />)}
          </div>
        ) : (
          <EmptyState icon="🧩" title="Aún no tienes servicios" hint="Cuando contrates un servicio aparecerá aquí." />
        ))}
    </div>
  );
}
