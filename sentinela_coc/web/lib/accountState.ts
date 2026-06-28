import type { Dashboard } from "@/lib/types";

// Estado de cuenta ÚNICO (derivado en la SPA del dashboard). Lo consumen el chip técnico
// del header y el hero (mensaje humano) -> ambos reflejan el MISMO estado, en distinto
// registro. Severidad: alerta > atencion > tranquilo.
export type AccountStatus = "tranquilo" | "atencion" | "alerta";

export function accountStatus(d?: Dashboard): AccountStatus {
  if (!d) return "tranquilo";
  if ((d.services?.suspended || 0) > 0) return "alerta";
  if ((d.billing?.overdue_amount || 0) > 0) return "atencion";
  return "tranquilo";
}
