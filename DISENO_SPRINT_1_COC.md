# Diseño — Sprint 1 (Portal COC) · Dashboard + Mis Servicios + Facturación (consulta)

> **Documento de diseño previo a implementación.** Construye sobre la plataforma base (WS-2 + WS-5 + EvoApi) ya en Producción (`coc-v1.0.0`). Disciplina: diseño → desarrollo → pruebas → despliegue.
> Estado: 📋 borrador para aprobación. **No iniciar código hasta aprobar.**

## 1. Objetivo y alcance
Que el cliente **consulte** sus servicios y su situación financiera desde el COC. **Solo lectura**, sin escrituras de negocio ni pagos.

**DENTRO (estricto):**
- **Dashboard del Portal** (estado de tranquilidad + tarjetas por servicio + pendientes).
- **Mis Servicios** (suscripciones del cliente).
- **Facturación (consulta únicamente)**: estado de cuenta, facturas/remisiones, CFDI (PDF+XML), historial de pagos.

**FUERA (no se toca en Sprint 1):** soporte/tickets, alarma/eventos, GPS, CCTV/acceso, pagos en línea, IA, notificaciones push, encuestas. Empresarial multi-sucursal completo (matriz/consolidado) = se aborda en un sprint posterior; **Sprint 1 entrega primero la experiencia residencial** de estas 3 áreas (decisión a confirmar).

## 2. Qué REUTILIZAMOS (no se reescribe)
### Odoo (fuente de verdad)
- `sentinela.subscription` — estado (`state`/`technical_state`/`billing_mode`), `product_id` (plan), `next_billing_date`, `recurring_interval`, `service_address_id`, contrato. **Ya scopeado por record rules (WS-2).**
- `account.move` — facturas/remisiones (`move_type` out_*), `payment_state`, `cfdi_status`, `cfdi_uuid` (FACTURA/REMISIÓN), `invoice_date(_due)`, `amount_total`. **Ya scopeado por record rules (WS-2).**
- **CFDI:** render PDF vía `ir.actions.report._render_qweb_pdf` (reusar; ver `sentinela_cfdi_prodigia`), campo `cfdi_xml` (+helpers `_get_*` timbrado, solo lectura). **No reimplementar el diseño de factura.**
- **Cobranza:** `om_account_followup` (`payment_amount_due`, unreconciled) para adeudo/estado de cuenta.
- **invoice_grouping_method** del partner (respetar al listar facturas).

### Plataforma base (WS-2/WS-5)
- **Aislamiento:** record rules + usuario portal lazy + **sesión Odoo efímera** → todo recurso corre como el cliente; no hay que re-implementar scoping.
- **Gateway:** `deps.current_session` (auth + access revocable), mapeo `portal_session.odoo_session_id` (act-as), `HttpOdooClient`, observabilidad (`/metrics`, logs `request_id`), patrón de serializadores DTO en `sentinela_api`.

## 3. Endpoints NUEVOS
> Recursos de negocio = en **`sentinela_api`** (auth='user' → corren como el usuario portal → record rules aplican). Serializadores DTO estables.

| Endpoint | Modelo / fuente | Método reusado | Scope |
|---|---|---|---|
| `GET /v1/services` | `sentinela.subscription` | search + serialize | record rules |
| `GET /v1/services/{id}` | `sentinela.subscription` | read + serialize | record rules |
| `GET /v1/billing/summary` | `account.move` + `om_account_followup` | composición (adeudo, próx. vencimientos) | record rules |
| `GET /v1/billing/invoices` | `account.move` (out_*) | search + serialize (paginado) | record rules |
| `GET /v1/billing/invoices/{id}` | `account.move` | read + serialize (incl. estatus timbrado) | record rules |
| `GET /v1/billing/invoices/{id}/pdf` | `account.move` | `_render_qweb_pdf` (bytes) | record rules + **caché** |
| `GET /v1/billing/invoices/{id}/xml` | `account.move.cfdi_xml` | bytes | record rules + **caché** |
| `GET /v1/billing/payments` | pagos del partner | search + serialize | record rules |
| `GET /v1/dashboard` | agregación | compone servicios + billing summary + estado | gateway (ver §4) |

- **Solo lectura** (GET). Errores RFC-7807. Paginación `?page&limit`.
- El scope lo garantizan las record rules (la sesión corre como el cliente) — **misma defensa que WS-2**.

## 4. Componentes del GATEWAY que participan
| Componente | Estado | Rol en Sprint 1 |
|---|---|---|
| `deps.current_session` | ✅ existe | Valida el access JWT (revocable) y obtiene la sesión |
| **Business proxy (BFF)** | 🆕 | Reenvía `/v1/services`, `/v1/billing/*` a Odoo **con el `odoo_session_id`** del cliente (act-as portal) y devuelve la respuesta. Es el puente SPA→Odoo (Odoo no es público). |
| **Caché** | 🆕 | PDF/XML de CFDI por `id+write_date` (se re-renderizan en cada llamada) + catálogos. |
| **Agregación Dashboard** | 🆕 | `/v1/dashboard` compone servicios + estado de cuenta + “estado de tranquilidad”; evita N+1 desde la SPA. |
| Observabilidad | ✅ existe | métricas/latencia/logs de los nuevos endpoints |
| **SPA (`web/`)** | 🆕 | Next.js: login (ya hay gateway) + Dashboard + Mis Servicios + Facturación (residencial) + branding por `/v1/config/theme`. |
| **Exposición `api.sentinela.mx`** | ⏳ pendiente RC1 | Se habilita en este Sprint (NPM/Cloudflare → gateway 8400) ya que la SPA es el primer consumidor. |

## 5. Pantallas del PRD cubiertas
**Residencial** (`WIREFRAMES_RESIDENCIAL_COC.md`):
- **Dashboard:** D-1 (verde), D-2 (ámbar/pendiente), D-3 (rojo, solo presentación; el detalle de evento es de otro sprint).
- **Mis Servicios:** tarjetas de servicio del dashboard + `MC-3` (servicios y contratos, vista de lectura).
- **Facturación:** `F-1` (estado de cuenta), `F-2` (lista), `F-3` (detalle + descarga PDF/XML), `F-4` (pagos).

**Empresarial** (`WIREFRAMES_EMPRESARIAL_COC.md`): NO en Sprint 1 (matriz `ED-1`, facturación consolidada `EB-*` → sprint posterior). *(Confirmar.)*

> Acciones marcadas “Fase 2/posterior” (pagar en línea, SOS, etc.) quedan fuera.

## 6. Criterios de aceptación por funcionalidad
### Dashboard
- Carga del “estado de tranquilidad” < 1 s percibido (agregación/caché; sin N+1 a Odoo).
- Muestra solo servicios del cliente; pendientes accionables (factura por vencer, contrato por firmar) derivados de datos reales.
- **Aislamiento:** un cliente nunca ve estado/datos de otro (prueba negativa).

### Mis Servicios
- Lista las suscripciones del cliente con estado (activo/suspendido), plan, próximo cobro, dirección.
- `state` vs `technical_state` reflejados correctamente (un “status” claro).
- **Aislamiento:** A no ve servicios de B (prueba negativa por recurso).

### Facturación (consulta)
- Estado de cuenta: adeudo total + próximos vencimientos correctos.
- Lista de facturas/remisiones con estado (pagada/pendiente/vencida); etiqueta FACTURA vs REMISIÓN por `cfdi_uuid`.
- Descarga **PDF y XML (CFDI)** correctos (bytes válidos), con caché.
- Historial de pagos del cliente.
- **Solo lectura** (sin acciones de escritura/pago). **Aislamiento:** A no ve/descarga facturas de B (prueba negativa, incl. IDOR por id).

## 7. Arquitectura / flujo
```
SPA (portal.sentinela.mx) → Gateway (api.sentinela.mx, Bearer access JWT)
   Gateway: current_session (valida + revocable) → act-as con odoo_session_id
   Gateway → Odoo sentinela_api /v1/services|billing (auth='user' = usuario portal)
   Odoo: record rules (WS-2) → SOLO datos del cliente → DTO
   Dashboard: el gateway agrega (servicios + billing summary) + caché
```

## 8. Secuencia (misma disciplina)
1. **Diseño** (este documento) → aprobación.
2. **Desarrollo:** serializadores + endpoints `sentinela_api` (con record rules ya existentes) → business proxy + caché + agregación en gateway → SPA (residencial).
3. **Pruebas:** unit (serializadores), **aislamiento por recurso** (A no ve B, IDOR), e2e (login→dashboard/servicios/facturas), smoke, rendimiento (caché PDF/XML).
4. **Despliegue:** STAGING-first → ventana → prod (incluye exponer `api.sentinela.mx`).

## 9. Pendientes / decisiones a confirmar
- ✅/❓ **Residencial primero** en Sprint 1 (empresarial multi-sucursal en sprint posterior). ¿Confirmas?
- ❓ **Dashboard:** ¿`/v1/dashboard` agregado en el gateway (recomendado, con caché) o un endpoint de agregación en Odoo?
- ❓ Alcance del “estado de tranquilidad” en v1 (con datos de servicios/facturación; los de alarma/internet llegan con sus módulos en sprints siguientes).
- Exposición pública `api.sentinela.mx` (heredada de RC1) se incluye en el despliegue de este Sprint.
