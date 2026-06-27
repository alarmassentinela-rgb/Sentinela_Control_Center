"use client";
import { useRouter } from "next/navigation";

import { Card } from "./ui/Card";
import { StatusPill } from "./ui/StatusPill";
import { serviceIcon } from "@/lib/format";
import type { Service } from "@/lib/types";

export function ServiceCard({ s }: { s: Partial<Service> }) {
  const router = useRouter();
  return (
    <Card onClick={() => router.push(`/servicios/${s.id}`)}>
      <div className="flex items-center gap-3">
        <div className="text-2xl" aria-hidden>{serviceIcon(s.service_type)}</div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2">
            <p className="truncate font-semibold text-ink">{s.service_type_label}</p>
            <StatusPill status={s.status} />
          </div>
          <p className="truncate text-xs text-muted">{s.plan || s.reference}</p>
        </div>
      </div>
    </Card>
  );
}
