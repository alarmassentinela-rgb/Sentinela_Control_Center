import type { ReactNode } from "react";

// Encabezado de pantalla del Design System. Estándar para toda pantalla con título
// (Servicios, Facturación y módulos futuros). El Dashboard NO lo usa: su encabezado es
// el hero "Estado de Tranquilidad".
export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="flex items-end justify-between gap-3 px-4 pb-3 pt-5">
      <div>
        <h1 className="text-title font-bold text-ink">{title}</h1>
        {subtitle && <p className="text-aux text-muted">{subtitle}</p>}
      </div>
      {actions}
    </header>
  );
}
