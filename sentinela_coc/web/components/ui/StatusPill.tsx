import { Badge, type BadgeTone } from "./Badge";
import { statusLabel } from "@/lib/format";

// Estado de servicio -> tono del Design System. Reutiliza <Badge> (única implementación
// de chips); aquí solo vive el mapeo de dominio status->tono+etiqueta.
const TONE: Record<string, BadgeTone> = {
  active: "ok",
  suspended: "danger",
  pending_signature: "warn",
  inactive: "neutral",
};

export function StatusPill({ status }: { status?: string }) {
  return <Badge tone={TONE[status || ""] || "neutral"}>{statusLabel(status)}</Badge>;
}
