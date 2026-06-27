"use client";
import { useRouter } from "next/navigation";

import { Card } from "./ui/Card";
import { cn } from "@/lib/cn";
import { formatDate, money } from "@/lib/format";
import type { Invoice } from "@/lib/types";

export function InvoiceRow({ inv }: { inv: Invoice }) {
  const router = useRouter();
  const paid = inv.payment_state === "paid";
  const label = inv.doc_type === "factura" ? "Factura" : "Remisión";
  return (
    <Card onClick={() => router.push(`/facturacion/${inv.id}`)}>
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-semibold text-ink">{inv.number || label}</p>
          <p className="text-xs text-muted">
            {formatDate(inv.date)} · {label}
          </p>
        </div>
        <div className="text-right">
          <p className="font-semibold text-ink">{money(inv.amount_total, inv.currency)}</p>
          <p className={cn("text-xs", paid ? "text-ok" : "text-warn")}>
            {paid ? "Pagada" : `${money(inv.amount_due, inv.currency)} por pagar`}
          </p>
        </div>
      </div>
    </Card>
  );
}
