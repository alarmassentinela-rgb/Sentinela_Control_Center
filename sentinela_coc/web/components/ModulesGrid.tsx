// Prepara la navegación para módulos que llegan en sprints posteriores.
// Se muestran como "Pronto" (no implementados en Sprint 1).
const MODULES = [
  { icon: "🛡️", label: "Alarmas" },
  { icon: "🌐", label: "Internet" },
  { icon: "📍", label: "GPS" },
  { icon: "💬", label: "Soporte" },
];

export function ModulesGrid() {
  return (
    <section className="space-y-2">
      <h2 className="px-1 text-aux font-semibold text-muted">Más módulos</h2>
      <div className="grid grid-cols-4 gap-2">
        {MODULES.map((m) => (
          <div
            key={m.label}
            className="flex flex-col items-center gap-1 rounded-card border border-slate-100 bg-surface p-3 text-center opacity-70"
            title="Próximamente"
          >
            <span className="text-2xl" aria-hidden>{m.icon}</span>
            <span className="text-caption text-muted">{m.label}</span>
            <span className="text-caption font-semibold text-brand">Pronto</span>
          </div>
        ))}
      </div>
    </section>
  );
}
