# Sprint 1 (Portal COC) — Plan · "Consulta: Mis Servicios + Facturación"

> **PLANIFICACIÓN — no iniciar implementación hasta cerrar el Go-Live del RC1.**
> Fase 1 del roadmap (PRD §10). Construye sobre la base segura (WS-2 + WS-5).

## 1. Objetivo
Primeros recursos de negocio del Portal: que el cliente **consulte sus servicios y su situación financiera** desde el COC. Lectura, sin escrituras de negocio ni pagos.

## 2. Alcance
**DENTRO:**
- **Mis Servicios:** lista de suscripciones (estado, plan, próximo cobro, dirección, contrato).
- **Facturación (solo consulta):** estado de cuenta (adeudo, próximos vencimientos), facturas/remisiones, **CFDI (PDF+XML)**, historial de pagos.
- **Dashboard "Estado de tranquilidad"** (agregado de servicios) — versión inicial.
- **SPA**: shell + estas pantallas (residencial primero).
**FUERA:** soporte/tickets, alarma/eventos, GPS, pagos en línea, IA, empresarial multi-sucursal completo (siguientes fases).

## 3. Recursos API (sobre `sentinela_api`, reusando lógica existente)
| Endpoint | Modelo Odoo | Clasif. |
|---|---|---|
| `GET /v1/services` · `/services/{id}` | `sentinela.subscription` (serializar state/technical_state/billing_mode) | ♻️ |
| `GET /v1/billing/summary` | `account.move` + `om_account_followup` (componer) | 🆕 composición |
| `GET /v1/billing/invoices` · `/{id}` | `account.move` | ♻️ |
| `GET /v1/billing/invoices/{id}/pdf` · `/xml` | render CFDI (`_render_qweb_pdf`, `cfdi_xml`) | ♻️ + caché |
| `GET /v1/billing/payments` · `/statement` | `account.move`/pagos | ♻️/🆕 |
| `GET /v1/dashboard` | agregación (gateway) | 🆕 |

Todos **scoped** por las record rules de WS-2 (sesión efímera del portal) + serializadores DTO estables.

## 4. Tareas (resumen)
- S1.1 Serializadores DTO (subscription, invoice, payment, dashboard).
- S1.2 Recursos `/v1/services*` (read) + tests de aislamiento por recurso.
- S1.3 Recursos `/v1/billing/*` (summary/invoices/pdf/xml/payments/statement) + caché de PDF/XML en gateway.
- S1.4 `/v1/dashboard` (estado de tranquilidad inicial).
- S1.5 SPA: login (ya existe gateway) + Mis Servicios + Facturación + dashboard (residencial).
- S1.6 Pruebas (unit + e2e por recurso: A no ve datos de B) + smoke.
- S1.7 Observabilidad de los nuevos endpoints (latencia/errores).

## 5. Dependencias / riesgos
- Requiere RC1 en Producción (base de identidad + aislamiento).
- CFDI PDF se re-renderiza por llamada → caché obligatoria (rendimiento).
- 43% subs sin teléfono → afecta adopción del login (campaña en paralelo).

## 6. Criterios de aceptación (borrador)
- Cliente ve **solo** sus servicios y facturas; descarga PDF+XML correctos.
- Aislamiento verificado por recurso (pruebas negativas).
- Dashboard carga rápido (caché/agregación); sin N+1 a Odoo.

> Detalle fino (tareas/estimación/pruebas) se completa al **abrir** el sprint, tras el Go-Live del RC1.
