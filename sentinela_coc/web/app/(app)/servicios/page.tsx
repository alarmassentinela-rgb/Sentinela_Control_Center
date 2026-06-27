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
    <div className="space-y-3 px-4 pb-4">
      <PageHeader title="Mis Servicios" />
      {loading && (
        <>
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </>
      )}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data &&
        (data.items.length ? (
          data.items.map((s) => <ServiceCard key={s.id} s={s} />)
        ) : (
          <EmptyState icon="🧩" title="Aún no tienes servicios" hint="Cuando contrates un servicio aparecerá aquí." />
        ))}
    </div>
  );
}
