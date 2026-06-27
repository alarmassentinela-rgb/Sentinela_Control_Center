"use client";
import { useParams } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { PageHeader } from "@/components/ui/PageHeader";
import { SkeletonText } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/States";
import { useQuery } from "@/hooks/useQuery";
import { apiGet, openDocument } from "@/lib/api";
import { formatDate, friendlyError, money } from "@/lib/format";
import type { Invoice } from "@/lib/types";

function Row({ k, v }: { k: string; v?: string | null }) {
  return (
    <div className="flex justify-between gap-4 border-t border-slate-100 pt-2 text-sm">
      <span className="text-muted">{k}</span>
      <span className="break-all text-right font-medium text-ink">{v || "—"}</span>
    </div>
  );
}

export default function FacturaDetallePage() {
  const params = useParams<{ id: string }>();
  const id = params?.id;
  const { data, loading, error, reload } = useQuery(() => apiGet<Invoice>(`/v1/billing/invoices/${id}`), [id]);
  const [busy, setBusy] = useState<string | null>(null);
  const [docErr, setDocErr] = useState<string | null>(null);

  async function download(kind: "pdf" | "xml") {
    setBusy(kind);
    setDocErr(null);
    try {
      await openDocument(`/v1/billing/invoices/${id}/${kind}`, `${data?.number || "documento"}.${kind}`);
    } catch (e) {
      setDocErr(kind === "xml" ? "Esta factura no tiene XML disponible." : friendlyError(e));
    } finally {
      setBusy(null);
    }
  }

  const label = data?.doc_type === "factura" ? "Factura" : "Remisión";

  return (
    <div className="space-y-3 px-4 pb-4 lg:mx-auto lg:max-w-2xl">
      <PageHeader title={label} />
      {loading && (
        <Card>
          <SkeletonText lines={6} />
        </Card>
      )}
      {error && <ErrorState message={error} onRetry={reload} />}
      {data && (
        <>
          <Card className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="font-bold text-ink">{data.number || label}</p>
              <span className="text-xs text-muted">{data.doc_type === "factura" ? "Factura (CFDI)" : "Remisión"}</span>
            </div>
            <Row k="Fecha" v={formatDate(data.date)} />
            <Row k="Vencimiento" v={formatDate(data.due_date)} />
            <Row k="Total" v={money(data.amount_total, data.currency)} />
            <Row k="Por pagar" v={money(data.amount_due, data.currency)} />
            {data.cfdi_uuid && <Row k="UUID" v={data.cfdi_uuid} />}
          </Card>

          {data.lines && data.lines.length > 0 && (
            <Card className="space-y-2">
              <p className="text-sm font-semibold text-ink">Conceptos</p>
              {data.lines.map((l, i) => (
                <div key={i} className="flex justify-between gap-3 border-t border-slate-100 pt-2 text-sm">
                  <span className="text-muted">{l.name}</span>
                  <span className="whitespace-nowrap font-medium text-ink">{money(l.price_subtotal, data.currency)}</span>
                </div>
              ))}
            </Card>
          )}

          <div className="flex gap-2">
            <Button className="flex-1" disabled={busy !== null} onClick={() => download("pdf")}>
              {busy === "pdf" ? "Abriendo…" : "Descargar PDF"}
            </Button>
            {data.has_xml && (
              <Button variant="secondary" className="flex-1" disabled={busy !== null} onClick={() => download("xml")}>
                {busy === "xml" ? "…" : "XML"}
              </Button>
            )}
          </div>
          {docErr && <p className="text-center text-sm text-danger">{docErr}</p>}
        </>
      )}
    </div>
  );
}
