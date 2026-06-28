# Auditoría Técnica y Arquitectónica — Módulo de Membresías (`sentinela_subscriptions`)

**Fecha:** 28 de junio de 2026 · **Tipo:** auditoría de **solo lectura** (no se modificó código, datos, ni la operación) · **Versión auditada:** `18.0.1.4.26` · **DB:** `Sentinela_V18` (producción).

> Solicitada para planear el crecimiento del ERP **sin** poner en riesgo la facturación recurrente actual. No contiene cambios; solo diagnóstico y recomendaciones.

---

## 0. Contexto y cifras (producción, 28-jun-2026)
- **394 suscripciones** totales: **362 activas**, 11 en suspensión, 16 canceladas, 4 borrador, 1 confirmada.
- `technical_state`: 367 activas, 11 suspendidas, 16 cortadas (estado de red, independiente del comercial).
- **1 sola empresa** (`res.company`), **373 direcciones de servicio** distintas (sucursales).
- Es un **motor de facturación recurrente propio** (Odoo 18 **Community**), construido sobre `sale`+`account`. **No** usa `sale_subscription` (Enterprise).

---

## 1. Arquitectura

### 1.1 Módulos/Modelos (`models/`)
- **Núcleo:** `sentinela.subscription` (en `subscription.py`, **2,589 líneas**). Hereda `mail.thread`+`mail.activity.mixin`.
- **Satélites de provisioning:** `sentinela.mikrotik.profile`, `sentinela.router`, `sentinela.flolive.service`, `sentinela.senticar.service`, `sentinela.subscription.gps.device`, `sentinela.gps.command.template`, matriz de servicios (`service_matrix.py`), `sentinela.contract.template`.
- **Extensiones:** `product.template` (planes), `res.partner` (datos fiscales/agrupación), `res.config.settings`.
- ⚠️ `subscription.py` **mezcla 5 clases**: `sentinela.subscription` + overrides de `sale.order`, `sale.order.line` y `account.move` (lógica de cobro adelantado).

### 1.2 Relaciones
- `subscription.partner_id` → cliente; `service_address_id` → sucursal; `product_id` → plan (producto).
- Provisioning: `router_id`, `mikrotik_profile_id`, `gps_device_ids`, `flolive`/`senticar` services.
- Facturación: `account.move.subscription_id` (1) **y** `subscription_ids` (M2M, para facturas agrupadas global/sucursal).
- Contrato: `sign_document_id` (firma digital), plantilla de contrato.

### 1.3 Estados (triple, bien separados)
- **`state` (comercial):** `draft → pending_signature → confirmed → active → suspension → closed/cancelled`.
- **`technical_state` (red):** `active / suspended (mora) / cut (retiro)` — decide el provisioning real.
- **`billing_mode`:** `normal` vs `courtesy` (activo pero sin facturar/cobrar). Solo manager lo edita.

### 1.4 Crones (`data/ir_cron_data.xml`)
| Cron | Cadencia | Rol |
|---|---|---|
| `ir_cron_generate_invoices` | diario | Genera pre-facturas del ciclo. |
| `ir_cron_auto_suspend_overdue` | diario | Suspende por mora. |
| `ir_cron_send_payment_reminders` | diario | Recordatorios. |
| `ir_cron_check_leasing_end` | diario | Fin de leasing. |
| `ir_cron_check_extensions` | horario | Cierra prórrogas. |
| `ir_cron_refresh_antenna_signal` | 15 min | Señal de antena (WISP). |
| `senticar_reconcile` / `cleanup_shares` | 6 h / diario | GPS. |

### 1.5 Facturación y renovaciones (flujo)
1. `_cron_generate_pre_invoices` busca subs `active` con `next_billing_date <= hoy` (no cortesía).
2. Las **agrupa** según `partner.invoice_grouping_method` (individual / by_branch / global; by_branch/global jalan las del **mismo mes calendario**).
3. `_billing_generate_invoice` crea **un `account.move` publicado** (líneas por plan, IVA del producto + posición fiscal), liga `subscription_ids`, y **avanza `next_billing_date`** un ciclo (`recurring_interval`, multi-mes).
4. **Renovación** = no hay objeto "renovación": la sub es **perpetua hasta cierre**; cada ciclo se factura y se avanza la fecha.
5. **Cobro adelantado** (overrides en `account.move`): `_advance_on_post` empuja `next_billing` al publicar; se revierte al cancelar o por nota de crédito (`_advance_*`).
6. **Anti-duplicado:** (a) avance de `next_billing_date` + (b) búsqueda de factura existente del mismo sub/grupo cuyo renglón contenga `_billing_period_label()`.

### 1.6 Dependencias
`base, mail, product, account, sale, sentinela_digital_sign, sentinela_cfdi_prodigia, om_account_followup`. Es decir: **Odoo Community + CFDI propio (Prodigia) + firma digital + cobranza OCA**.

---

## 2. Calidad del diseño — fortalezas y debilidades

**Fortalezas**
- ✅ **Separación estado comercial / técnico / billing_mode**: excelente para un negocio que mezcla facturación con provisioning (WISP/alarma/GPS). Pocos ERPs lo modelan tan limpio.
- ✅ **Agrupación de facturación flexible** (individual/sucursal/global) ya en producción.
- ✅ **Suspensión/reactivación endurecida** (walled-garden + verificación por firewall, corte de sesión) — robusto y battle-tested.
- ✅ **Impuestos vía producto + posición fiscal** (nativo, correcto fiscalmente).
- ✅ Sin **lock-in Enterprise**: todo Community.

**Debilidades**
- ⚠️ **Monolito** `subscription.py` (2,589 líneas, 5 clases) — difícil de mantener y de migrar.
- ⚠️ **Sin pruebas automatizadas** (no existe `tests/`) en un módulo **crítico**.
- ⚠️ **Idempotencia "lógica"** del billing (avance + búsqueda por etiqueta de texto), no por **clave única** en BD.
- ⚠️ **Sin índices** de negocio (solo PK) y **cron en una sola transacción** (ver §5/§6).
- ⚠️ **Single-company** (sin `company_id`).

---

## 3. Integración con el Motor de Catálogo — ¿independientes?

**Sí, y deben seguir así.** El único punto de contacto **correcto** es **`product.template`**: los planes de membresía son *productos propios*. El Motor de Catálogo (híbrido) clasifica como *propios* justamente a los productos **sin `product.supplierinfo` de distribuidor** → los planes de membresía **quedan fuera** del alcance de los conectores/sincronización de catálogo.

- **No hay acoplamiento:** Membresías **consume** `product.template`; el Catálogo **alimenta** `product.template`/`supplierinfo` para productos de distribuidor. Vías distintas, modelo maestro compartido.
- **Recomendación:** que el scheduler del Catálogo **nunca** toque productos marcados como propios/plan (filtrar por "tiene supplierinfo de distribuidor"). Y que Membresías **no dependa** de ningún módulo del Catálogo. Acoplamiento = **cero**.

---

## 4. ¿Membresías como productos/servicios de Odoo, o alternativa?

**Recomendación: mantener la representación actual** (plan = `product.template` tipo servicio + modelo `sentinela.subscription` para el contrato/ciclo/provisioning).
- **Por qué es correcta:** los planes-como-productos integran nativamente con `sale`, `account`, impuestos, CFDI y reportes. El modelo `subscription` aporta lo que Odoo nativo NO tiene (ciclo recurrente Community + provisioning de red/GPS + estados técnicos).
- **Alternativas evaluadas (no recomendadas ahora):**
  - **Odoo Enterprise `sale.subscription`:** implicaría Enterprise (costo + lock-in) y aún así no cubre el provisioning. **No.**
  - **OCA `contract`** (facturación recurrente Community): sólido para la *recurrencia pura*, pero migrar el motor actual (que ya funciona y carga provisioning) es **alto riesgo / bajo beneficio** hoy. Anotarlo como **referencia** para una eventual modularización, no como reemplazo.

---

## 5. Facturación recurrente — análisis de riesgos

| Riesgo | Estado actual | Severidad |
|---|---|---|
| **Duplicados** | Mitigado por avance de `next_billing` + búsqueda por `_billing_period_label()` (ilike). **Riesgo real:** si el **formato de la etiqueta cambia** (ocurrió en evolución reciente del PDF/labels), una factura previa podría **no coincidir** y duplicarse; y la búsqueda es por texto, no clave única. | 🔴 Alta |
| **Carreras de concurrencia** | El `ir.cron` evita auto-solape (lock de cron). **Pero** no hay `SELECT FOR UPDATE`: cron + facturación manual simultáneas podrían competir; la única red es la búsqueda lógica. | 🟠 Media |
| **Cancelaciones** | Cubierto: nota de crédito revierte el adelanto (`_advance_on_unpost`/refund). | 🟢 OK |
| **Renovaciones** | Perpetua por avance de fecha; correcto para el modelo. | 🟢 OK |
| **Cambios de plan** | Cambia producto/perfil; **sin prorrateo** del ciclo en curso. | 🟠 Media |
| **Prorrateos** | **No implementado.** Alta/baja/cambio a mitad de ciclo no se prorratea. | 🟠 Media |
| **Descuentos** | El cron arma líneas por `price_unit`; **no modela descuentos** en el recurrente (sí existe el campo nativo en venta, no se usa en la generación). | 🟡 Baja-Media |
| **Impuestos** | Vía producto + posición fiscal (nativo). | 🟢 OK |
| **Suspensiones/Reactivaciones** | Endurecido (walled-garden + firewall + corte de sesión). | 🟢 OK |

**Hallazgo principal de riesgo:** la **idempotencia del billing depende de una búsqueda por texto de la etiqueta de periodo**. Es el punto más frágil ante duplicados; una **clave única** (p. ej. `unique(subscription_id, periodo_normalizado)` o un campo `billing_key`) lo blindaría — **mejora futura, no urgente para el volumen actual**.

---

## 6. Escalabilidad

| Escenario | ¿Soporta hoy? | Análisis |
|---|---|---|
| **Miles de membresías** | ⚠️ Con riesgo | El cron de facturación corre en **UNA transacción sin commits por lote** (mismo anti-patrón que tenía Syscom). A 394 subs va bien; a miles, riesgo de **timeout/memoria**. |
| **Cientos de facturas/día** | ⚠️ Con riesgo | El lote mensual (~240+ a la vez el día 1) funciona; escalar requiere **batching + commit por grupo**. |
| **Multi-empresa** | ❌ No | **No hay `company_id`** en la suscripción; diseño single-company. |
| **Multi-sucursal** | ✅ Sí | `service_address_id` + agrupación by_branch (373 direcciones hoy). |
| **Consultas a escala** | ⚠️ | **Solo índice PK**; falta índice en `next_billing_date`, `state`, `partner_id`, `billing_mode` → escaneos completos a volumen alto. |

---

## 7. Integración futura (sin modificar lo actual)

- **Portal del Cliente / App móvil:** ya hay base — `sentinela_api` (Portal COC) expone suscripciones por REST. Consumible sin tocar el módulo.
- **IA:** los datos (subs, facturas, estados, periodos) son estructurados; un agente puede leerlos vía la API/XML-RPC para predicción de churn, cobranza inteligente, etc. **Sin cambios al módulo.**
- **CRM / Mesa de ayuda:** la sub ya liga `partner_id` y órdenes FSM; integrar CRM/helpdesk = relaciones por `partner_id`, no requiere refactor.
- **Monitoreo:** ya integrado (alarma/GPS via los satélites + FSM).
- **Motor de Catálogo:** independiente (§3); comparten solo `product.template`.
- **Recomendación:** toda integración futura debe ser **read-mostly vía la capa API**, no por dependencias nuevas en `sentinela_subscriptions` (evita acoplar el corazón).

---

## 8. Compatibilidad con futuras versiones de Odoo

Puntos que **dificultarían** una migración mayor (orden de impacto):
1. **Overrides de `account.move` / `sale.order`** (cobro adelantado, `action_post`) — los métodos core cambian entre versiones; requieren revalidación en cada upgrade.
2. **CFDI propio** (`sentinela_cfdi_prodigia`, sin `l10n_mx_edi`) — dependencia acoplada, sensible a cambios de `account`.
3. **Monolito de 2,589 líneas** con 5 clases — mayor superficie de cambio.
4. **Dependencia OCA `om_account_followup`** — debe existir versión compatible por cada release Odoo.
5. Vistas ya en sintaxis Odoo 18 (`list`) — OK.
> **A favor:** sin Enterprise → no hay bloqueos de licencia; la migración es trabajo de ingeniería, no de plataforma.

---

## 9. Deuda técnica (priorizada)

**🔴 Críticas** (blindan la operación; mejoras quirúrgicas sin cambiar comportamiento)
1. **Idempotencia por clave única** del billing (hoy búsqueda por texto de etiqueta) → riesgo de duplicados.
2. **Batching + commit por grupo** en el cron de facturación → evita timeout/memoria a escala.
3. **Índices** en `next_billing_date`, `state`, `partner_id`, `billing_mode`.

**🟠 Importantes**
4. **Pruebas automatizadas** del flujo de facturación (módulo crítico hoy **sin tests**).
5. **Modularizar** `subscription.py` (separar overrides de `account.move`/`sale.order` a archivos propios) — facilita mantenimiento y upgrade.
6. **Observabilidad** del cron (cuántas generó, fallos, duración) — hoy solo `_logger.error`.
7. **Prorrateo** y **descuentos** en el recurrente (si el negocio lo requiere).

**🟡 Deseables**
8. `company_id` / preparación multi-empresa (cuando se necesite).
9. Evaluar OCA `contract` como base de la recurrencia pura (estudio, no migración).
10. Documentar el flujo de facturación (diagramas) para onboarding.

---

## 10. Recomendación

- **¿La arquitectura actual es suficiente?** **Sí, para la operación actual** (394 subs, 1 empresa). Está en producción, cumple, y los flujos críticos (suspensión, CFDI, agrupación, cobro adelantado) funcionan.
- **¿Conviene mantenerla?** **Sí.** **No reemplazar ni refactorizar ahora** — el riesgo supera al beneficio y la operación es estable.
- **¿Conviene evolucionarla gradualmente?** **Sí** — atacar las **3 críticas** como mejoras **quirúrgicas y reversibles** (índices, batching/commit, clave única anti-duplicado), todas **sin cambiar el comportamiento** visible. Después, las importantes (tests, modularización).
- **¿Conviene reemplazarla en el futuro?** **No en el corto/mediano plazo.** Solo si aparece un requisito fuerte (multi-empresa real, decenas de miles de subs): entonces **evolucionar/modularizar** (no reescribir), posiblemente apoyándose en patrones OCA, conservando el provisioning propio.

### Veredicto sobre la convivencia con el Motor de Catálogo
**No hay conflicto ni acoplamiento.** Membresías y Catálogo son independientes y comparten únicamente el catálogo maestro de productos (`product.template`). Ninguna decisión del Catálogo descrita en el Blueprint afecta la facturación recurrente. Se recomienda formalizar la regla: **el Catálogo solo gestiona productos con proveedor-distribuidor; los planes de membresía (productos propios) quedan fuera de su sincronización.**

---

> **Recordatorio:** este documento es **solo auditoría**. No se ejecutó ningún cambio. Cualquier mejora de §9 se haría, en su momento, por fases, en STAGING, reversible y con tu aprobación — igual que el Motor de Catálogo.

### Apéndice — Fuentes
Código: `sentinela_subscriptions/` (`subscription.py` 2,589 líneas, `__manifest__.py`, `data/ir_cron_data.xml`). Datos: consultas SQL de solo lectura a `Sentinela_V18` (estados, conteos, índices, empresas, direcciones). Sin escrituras.
