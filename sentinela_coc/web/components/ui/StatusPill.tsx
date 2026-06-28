import { cn } from "@/lib/cn";
import { statusLabel } from "@/lib/format";

const MAP: Record<string, string> = {
  active: "bg-green-100 text-green-700",
  suspended: "bg-red-100 text-red-700",
  pending_signature: "bg-amber-100 text-amber-700",
  inactive: "bg-slate-100 text-slate-600",
};

export function StatusPill({ status }: { status?: string }) {
  return (
    <span className={cn("inline-flex rounded-full px-2.5 py-1 text-xs font-semibold", MAP[status || ""] || "bg-slate-100 text-slate-600")}>
      {statusLabel(status)}
    </span>
  );
}
