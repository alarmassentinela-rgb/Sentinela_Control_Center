"use client";
import { Button } from "./Button";

// Paginación incremental del Design System. SOLO presentacional (sin lógica de negocio
// ni de datos: la paginación vive en el hook usePaged). Reutilizable en cualquier listado
// (Facturas, Pagos, Notificaciones, Historial, Tickets, Auditoría). No conoce el dominio.
export function LoadMore({
  shown,
  total,
  loading,
  onMore,
}: {
  shown: number;
  total: number;
  loading: boolean;
  onMore: () => void;
}) {
  if (total <= 0) return null;
  const hasMore = shown < total;
  return (
    <div className="flex flex-col items-center gap-2 py-3 text-caption text-muted">
      <p>Mostrando {shown} de {total}</p>
      {hasMore ? (
        <Button variant="secondary" onClick={onMore} disabled={loading}>
          {loading ? "Cargando…" : "Cargar más"}
        </Button>
      ) : (
        <p>No hay más resultados</p>
      )}
    </div>
  );
}
