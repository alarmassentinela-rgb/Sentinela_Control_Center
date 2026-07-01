# MEJORAS_CONTINUAS_COC — Backlog vivo del Portal COC

Backlog de mejoras/refactors **diferidos** (no bloquean Go-Live). Se revisa al inicio de cada Sprint. Origen: auditoría de Go-Live Sprint 1 (28-jun-2026) salvo que se indique otra cosa.

> Reglas: nada aquí afecta funcionalidad ni seguridad del cliente. Son deuda técnica de bajo impacto, consistencia interna y mejoras futuras.

## 🟡 Recomendables (deuda técnica de bajo impacto)

### Design System — consolidación
- **Color de estado definido 3 veces:** `components/ui/StatusPill.tsx` (`MAP`), `components/AppHeader.tsx` (`generalState`) y badge en `app/(app)/dashboard/page.tsx:50`. Centralizar en un único mapa de tonos (idealmente reutilizar `StatusIndicator`/un `Badge` del DS).
- **Badge "Vencido" duplicado:** `dashboard/page.tsx:50` copia el estilo de `StatusPill` en vez de usar el componente.
- **Contenedores tipo Card reinventados:** `ModulesGrid.tsx:18`, `NextActions.tsx:36`, `SelectionBar.tsx:20` construyen tarjetas a mano con tokens distintos (`border-slate-100` vs `-200`, `shadow-sm` vs `shadow-lg`, `p-3` vs `p-4`). Unificar contra `ui/Card`.
- **Componentes DS faltantes** (hoy inline): `ui/Input` (login), `ui/Alert` (login + PaymentSummaryModal), `ui/Tabs` (facturación), `ui/Badge`.
- **Tokens inconsistentes:** radios (`rounded-xl` / `rounded-xl2` / `rounded-lg`), y tamaños sueltos `text-[9px]/[10px]/[11px]` repartidos en ~20 lugares → mover a tokens en `tailwind.config.ts` (p. ej. `text-meta`, `text-caption`).

### Limpieza de código
- **`gateway/perf_bench.py`**: script de benchmark en la raíz del gateway; no debe desplegarse a producción (excluir del deploy o mover a `tools/`).
- **`components/ui/icons.tsx:32` `UserIcon`**: exportado y sin usar → eliminar.
- **`gateway/app/config.py:42` TODO**: driver WhatsApp (EvoApi) por entorno → confirmar valores de producción (parte del checklist Go-Live).

### Accesibilidad (no núcleo)
- **`BottomNav` "Soporte"** deshabilitado es `<div title>`; cuando exista el módulo de Soporte, definir su interacción real (`<button>`/`aria-disabled`/ruta). *Diferido por decisión: el módulo aún no existe.*
- **Tabs de Facturación**: agregar `role="tablist"/role="tab"/aria-selected` (hoy son `<button>` operables, falta semántica ARIA fina).
- **AppHeader** botones reservados (campana/IA): añadir `aria-label` explícito (hoy `title`, y están `disabled`).

## 🟢 Mejoras futuras
- Escala tipográfica y de espaciado formal en el DS (elimina los `text-[Npx]` sueltos).
- Suite de componentes DS (Input, Alert/Toast, Tabs, Badge) documentada para nuevas pantallas.
- **Favicon de marca real** (hoy placeholder neutro `app/icon.svg`) + `title`/`description` del documento derivados del branding de Odoo.
- `focus-visible` consistente en todos los interactivos (más allá de lo corregido en el lote de a11y).
- **Búsqueda/filtro de facturas** por mes/folio para clientes con cientos de documentos (complemento de la paginación "Cargar más").
- Señal de entrega de OTP sin romper la neutralidad del mensaje.
- Distinguir OTP expirado vs inválido (B2, diferido por decisión de producto).

## [Sprint 3 · deuda técnica · UAT-002] Sustituir SUPERUSER_ID en /coc/internal/payments/apply
- **Origen:** UAT-002 del Sprint 2 (aplicación de pago). El posteo contable via `account.payment.register.action_create_payments()` no honra el flag `su` de `.sudo()` → el usuario público (uid 4) provoca `AccessError` en `account.move`.
- **Decisión controlada Sprint 2:** ejecutar el bloque con `SUPERUSER_ID` (no existía usuario técnico con permisos de contabilidad; no se autorizó crear usuarios en el release).
- **Objetivo Sprint 3:** sustituir `SUPERUSER_ID` por un **usuario técnico dedicado** (interno, share=False, con solo los permisos de contabilidad necesarios) o mecanismo equivalente, para restaurar la evaluación de ACLs (su=False) en el endpoint interno.
- **Archivo:** `sentinela_api/controllers/payments.py` (método `apply`).
