# Documento Técnico de Implementación — Portal COC Sentinela

> **Puente entre el diseño funcional (PRD + wireframes) y el desarrollo.**
> Relaciona cada pantalla con: módulos Odoo · modelos de datos · APIs · reglas de seguridad · dependencias técnicas · prioridad/fase.
> Referencias: `PRD_PORTAL_COC_SENTINELA.md`, `WIREFRAMES_RESIDENCIAL_COC.md`, `WIREFRAMES_EMPRESARIAL_COC.md`.
> Versión 1.0 · 2026-06-25. Basado en las auditorías de reutilización y técnica (sesión 25-jun).

## Leyenda
- **♻️ REUSAR** (modelo/método ya existe y es exponible) · **🔧 REFACTOR** (existe pero hay que extraer/adaptar) · **🆕 CONSTRUIR**.
- Fase = roadmap PRD §10. Prioridad: M(ust)/S(hould)/C(ould)/W(on't v1).

---

## 1. Arquitectura de referencia y componentes a construir

```
SPA (Next.js) / App móvil ──HTTPS+JWT──► API GATEWAY (FastAPI, BFF)
                                          │ identidad, OTP, agregación, caché, ruteo notif
                                          └──LAN, service account──► sentinela_api (addon REST Odoo)
                                                                      └──ORM/métodos──► sentinela_* + integraciones
```

**Componentes NUEVOS del proyecto:**

| Componente | Tipo | Rol | Estado |
|---|---|---|---|
| `sentinela_api` | Addon Odoo 18 | REST/JSON + serializadores + **record rules de portal** | 🆕 (release/deploy con skills) |
| COC Gateway | FastAPI + Docker | Identidad/JWT/OTP, agregación, caché, ruteo de notificaciones, drivers | 🆕 (standalone) |
| COC Web | Next.js + Docker | SPA del portal | 🆕 (standalone) |
| COC Mobile | (futuro) | App sobre la misma API | Fase 5 |

---

## 2. Convenciones de la API (`/v1`)

- **Auth:** `Authorization: Bearer <JWT>`. JWT contiene `partner_id`, `org_id?`, `role`, `scopes`, `sucursal_ids?`.
- **Versionado:** prefijo `/v1`. **Paginación:** `?page&limit`. **Errores:** RFC-7807. **DTOs estables** (un cambio de modelo Odoo no rompe al cliente).
- **Caché (gateway):** PDF/XML por `id+write_date`; catálogos (prioridades, códigos) por TTL.
- **Scope:** todo recurso filtra por `partner_id` del token (residencial) o por `partner` + `sucursal_ids` (empresarial), validado **también en Odoo** (record rules).

---

## 3. Modelo de seguridad transversal

| Capa | Mecanismo | Detalle |
|---|---|---|
| Aislamiento de identidad | Gateway | `portal_identity` mapea teléfono/email → `partner_id`. NO se crean `res.users` por cliente. |
| Autenticación | Gateway | OTP WhatsApp (canal transaccional) + contraseña (argon2) + biométrico; magic links solo firma/autorización. |
| Autorización (roles) | Gateway (JWT scopes) | Roles **data-driven** (Titular/Operador-Flotilla/Contabilidad/Lectura) extensibles sin tocar lógica. Permisos limitables por **sucursal/servicio/módulo**. |
| **Aislamiento de datos (BLOQUEADOR)** | **Odoo record rules** 🆕 | Reglas de partner en `sentinela.subscription`, `sentinela.alarm.event`, `sentinela.sign.document` (hoy NO existen). `account.move`, `fsm.order`, `monitoring.device` revisar/añadir. Backstop a nivel datos, no solo gateway. |
| Scope por sucursal | Dominio | `service_address_id child_of partner_id` filtrado por `sucursal_ids` del token. |
| Secretos | `ir.config_parameter` / env / vault | Nunca en repo. |
| Auditoría | Gateway | Log de acceso (user, partner, recurso, IP). |

> **Fase 0 obligatoria:** crear las record rules de portn antes de exponer cualquier recurso.

---

## 4. Mapeo técnico por capacidad

### 4.1 Identidad, Perfil y Configuración
- **Pantallas:** O-1/O-2/O-3, L-1…L-5, EA-1, MC-1/MC-2/MC-5, D-1/ED-1 (theme).
- **Módulos Odoo:** `base` (`res.partner`), `sentinela_subscriptions` (extensión partner).
- **Modelos/métodos:** ♻️ `res.partner`; ♻️ `find_partner_by_phone` (de `chatwoot_bot/odoo.py`, patrón a portar al gateway); 🆕 `portal_identity`, `otp_code`, roles/scopes (gateway).
- **APIs:** `POST /v1/auth/otp/request|verify`, `/login`, `/refresh`, `/recover`, `/logout`; `GET/PUT /v1/me`; `POST /v1/me/devices`; `GET /v1/config/theme` (público por host — costura branding).
- **Seguridad:** rate-limit OTP; JWT corto + refresh; theme público sin datos sensibles.
- **Dependencias:** driver de mensajería (WhatsApp/EvoApi) para OTP; vault de credenciales.
- **Fase/Prioridad:** Fase 0 · M.

### 4.2 Dashboard / Tablero (agregación)
- **Pantallas:** D-1/D-2/D-3 (res), ED-1/ED-2/ED-3 (emp).
- **Módulos:** transversal (subscriptions, monitoring, fsm, account).
- **Modelos:** ♻️ `sentinela.subscription` (state/technical_state), `monitoring.device.last_communication`, `alarm.event`, `account.move`; 🆕 **composición "Estado de tranquilidad"/matriz servicios×sucursal en el gateway**.
- **APIs:** `GET /v1/dashboard` (agregado), `GET /v1/dashboard/sites` (empresarial), `GET /v1/alerts`.
- **Seguridad:** scope partner/sucursal; solo lectura.
- **Dependencias:** caché de agregación (Redis); health scores (§4.4).
- **Fase/Prioridad:** Fase 1 · M.

### 4.3 Seguridad / Alarma
- **Pantallas:** S-1…S-6 (res), ES-1…ES-3 (emp).
- **Módulos:** `sentinela_monitoring` (+ `sentinela_fsm` patrulla).
- **Modelos/métodos:** ♻️ `sentinela.alarm.event` (+ `_render_master_report_pdf`, `get_fsm_orders_info`), `sentinela.monitoring.device` (battery_level, signal_strength, last_communication, connection_mode), `service.authorization.token` (`authorize/reject`), `res.partner.notify` (click-to-call/contactos); 🔧 estado CA derivado de eventos Contact-ID (E301/R301); 🆕 `get_health_status`, `get_partner_events` (método de servicio).
- **APIs:** `GET /v1/alarm/events`, `/events/{id}`, `/events/{id}/report` (PDF), `/alarm/devices` (salud), `POST /v1/alarm/authorizations/{token}`.
- **Seguridad:** 🆕 **record rule en `alarm.event`** (bloqueador); magic link autorización con TTL+lock+auditoría (♻️).
- **Dependencias:** caché PDF; bus.bus (tiempo real = Fase 4).
- **Fase/Prioridad:** eventos Fase 1–2; núcleo Fase 2 · M.

### 4.4 Salud de dispositivos (health score)
- **Pantallas:** D-1/S-1 (latido/estado), ES-1.
- **Modelos/métodos:** ♻️ `monitoring.device` (last_communication vs expected_heartbeat) · GPS diag (`flolive_service.get_sim_diagnostics`); 🆕 `get_health_status()` (computo healthy/warning/offline).
- **APIs:** `GET /v1/services/{id}/health`, incluido en dashboard.
- **Fase/Prioridad:** Fase 1 (alarma) → 2 (telemetría) · M/S.

### 4.5 Internet
- **Pantallas:** I-1/I-2 (res), EI-1/EI-2 (emp).
- **Módulos:** `sentinela_subscriptions` + standalone `sentinela_netwatch` (TimescaleDB).
- **Modelos:** ♻️ `subscription.conn_online/antenna_signal_dbm/live_traffic_status`; 🔧 **consumo histórico** = TSDB netwatch (tabla `traffic*`, mapear pppoe_user→subscription) — endpoint nuevo o lectura directa.
- **APIs:** `GET /v1/internet/{service_id}/status`, `/usage` (Fase 2).
- **Seguridad:** scope partner/sucursal; credenciales TSDB por env.
- **Dependencias:** netwatch (consumo, status por zona = Fase 2).
- **Fase/Prioridad:** estado Fase 1–2 · M; consumo/diagnóstico Fase 2 · S.

### 4.6 GPS / Flotilla
- **Pantallas:** (res GPS no en este lote) · EF-1…EF-5 (emp).
- **Módulos:** `sentinela_subscriptions` (GPS) + Traccar/SentiCar + floLIVE.
- **Modelos/métodos:** ♻️ `sentinela.senticar.service` (`create_share_link`, `list_devices`), `sentinela.subscription.gps.device`, `get_last_location_from_traccar`, `flolive_service.*` (diag/SMS). Inmovilizar = ♻️ comandos SMS GPS (Fase 2–3).
- **APIs:** `GET /v1/gps/units`, `/units/{id}/position`, `/units/{id}/history`, `POST /v1/gps/units/{id}/share`; `/gps/alerts`; `/gps/reports`.
- **Seguridad:** scope partner/sucursal; compartir = token temporal (♻️).
- **Dependencias:** driver GPS (Traccar) con retry (matar `except:pass` en `senticar_service.py`).
- **Fase/Prioridad:** Fase 2–3 · M(emp)/S.

### 4.7 Facturación (solo consulta v1)
- **Pantallas:** F-1…F-4 (res), EB-1…EB-3 (emp).
- **Módulos:** `account`, `sentinela_cfdi_prodigia`, `om_account_followup`.
- **Modelos/métodos:** ♻️ `account.move` (PDF vía `_render_qweb_pdf`, `cfdi_xml`, helpers timbrado solo-lectura, `cfdi_uuid`→FACTURA/REMISIÓN), `om_account_followup` (adeudo); 🆕 composición **estado de cuenta** + **CFDI masivo (ZIP)** en gateway.
- **APIs:** `GET /v1/billing/summary|invoices|invoices/{id}|/{id}/pdf|/{id}/xml|payments|statement`; `GET /v1/billing/cfdi/bulk` (empresarial).
- **Seguridad:** 🆕 record rule / check de partner en `account.move` (hoy ad-hoc); solo lectura (NO exponer timbrado).
- **Dependencias:** caché PDF/XML; respeta `invoice_grouping_method`.
- **Fase/Prioridad:** Fase 1 · M. (Pago en línea = Fase 5.)

### 4.8 Equipos y Mantenimiento
- **Pantallas:** S-7 (res), ED-2/EAD (emp equipos por sitio).
- **Módulos:** `sentinela_subscriptions` (equipment_ownership, leasing), `sentinela_fsm` (mantenimiento).
- **Modelos:** ♻️ `fsm.order` (service_type=maintenance, historial), `subscription` (equipment_ownership, fin de leasing, next_maintenance), `fsm.equipment`; **🆕 garantía + vida útil = modelo específico (FASE POSTERIOR, decisión A aprobada).**
- **APIs:** `GET /v1/equipment`, `/equipment/{id}`, `/maintenance/history`, `/maintenance/next`.
- **Fase/Prioridad:** v1 = equipos+propiedad+mantenimiento básico (Fase 2); garantía/vida útil = fase posterior.

### 4.9 Soporte / Tickets / Tracking / Chat / Encuesta
- **Pantallas:** SP-1…SP-5 (res), ESU-1…ESU-3 (emp).
- **Módulos:** `sentinela_fsm` (+ Traccar para tracking).
- **Modelos/métodos:** ♻️ `sentinela.fsm.order` (estados, tracking_token), `get_last_location_from_traccar`, `fsm.chat.message` (`create_message/get_chat_messages`), `register_survey_response`; 🔧 **extraer `create_from_customer_request()`** del controller a método de modelo.
- **APIs:** `GET/POST /v1/tickets`, `/tickets/{id}`, `/tickets/{id}/tracking`, `/tickets/{id}/messages`, `POST /v1/tickets/{id}/survey`.
- **Seguridad:** record rules/scope por partner+sucursal; tracking degrada elegante si Traccar falla.
- **Dependencias:** driver Traccar; 🔧 método de creación.
- **Fase/Prioridad:** Fase 1–2 · M.

### 4.10 Notificaciones (centro + ruteo + push)
- **Pantallas:** N-1 (res), EN/EAD-4 (emp ruteo por rol).
- **Módulos:** `sentinela_monitoring` (`res.partner.notify`), gateway.
- **Modelos/métodos:** ♻️ `partner.notify()` (Telegram/WhatsApp/email); 🆕 **centro de notificaciones** (bandeja + push tokens) y **reglas de ruteo por rol** en gateway.
- **APIs:** `GET /v1/notifications`, `PUT /v1/notifications/preferences`, `POST /v1/me/devices` (push).
- **Fase/Prioridad:** Fase 1 · M.

### 4.11 Sugerencias y comentarios
- **Pantallas:** MC-6 (res), accesible emp.
- **Modelos:** 🆕 `sentinela.suggestion` (modelo ligero).
- **APIs:** `POST /v1/suggestions`, `GET /v1/suggestions`.
- **Fase/Prioridad:** Fase 1 · M (pequeño).

### 4.12 Administración (empresarial)
- **Pantallas:** EAD-1 (usuarios/roles), EAD-2 (sucursales), EAD-3 (contratos), EAD-4 (notif).
- **Módulos:** `base` (res.partner child_of), `sentinela_digital_sign` (contratos), gateway (roles).
- **Modelos/métodos:** ♻️ `res.partner` (sucursales = child_of), `sign_document.action_sign`; 🆕 gestión de usuarios/roles/alcance por sucursal (gateway).
- **APIs:** `GET/POST/PUT /v1/org/users`, `/org/sites`, `GET /v1/contracts`, `POST /v1/contracts/{id}/sign`.
- **Seguridad:** solo rol Titular/Admin; firma = magic link.
- **Fase/Prioridad:** Fase 1–2 · M/S.

### 4.13 CCTV / Control de Acceso
- **Pantallas:** placeholder "Próximamente" (res y emp).
- **Estado:** 🆕 telemetría requiere definir fuente (NVR/controladora). v1 = solo placeholder.
- **Fase/Prioridad:** Fase 5+ · W(v1).

---

## 5. Componentes nuevos a construir (resumen)

| Componente | Tipo | Fase |
|---|---|---|
| Record rules de portal (subscription/alarm.event/sign.document/account.move) | Odoo security 🆕 | **0 (bloqueador)** |
| `sentinela_api` (addon REST + serializadores) | Odoo 🆕 | 0→continuo |
| Gateway: identidad/OTP/JWT/roles | FastAPI 🆕 | 0 |
| Gateway: agregación dashboard + health score | FastAPI 🆕 | 1 |
| Gateway: caché (PDF/XML/catálogos) | FastAPI 🆕 | 1 |
| Drivers de integración (MikroTik/Traccar/floLIVE/Prodigia/Messaging) | Adaptadores 🆕/🔧 | 0.5 |
| `sentinela.suggestion` | Odoo 🆕 | 1 |
| Centro de notificaciones + push + ruteo por rol | Gateway 🆕 | 1 |
| Composición estado de cuenta + CFDI masivo | Gateway 🆕 | 1 |
| `create_from_customer_request()` (extracción) | Odoo 🔧 | 1–2 |
| `get_health_status()` | Odoo 🆕 | 1–2 |
| Modelo equipos (garantía/vida útil) | Odoo 🆕 | fase posterior |
| Consumo internet (TSDB netwatch) | netwatch/gateway 🔧 | 2 |
| SSE/WebSocket (tiempo real) | Gateway 🆕 | 4 |

---

## 6. Matriz de trazabilidad (pantalla → capacidad → endpoints → fase)

| Pantallas | Capacidad | Endpoints principales | Fase |
|---|---|---|---|
| O/L/EA, MC-1/2/5 | Identidad/Perfil | `/v1/auth/*`, `/v1/me` | 0 |
| (todas) | Branding | `/v1/config/theme` | 0 |
| D-1..3, ED-1..3 | Dashboard/Tablero | `/v1/dashboard`, `/dashboard/sites`, `/alerts` | 1 |
| S-1..6, ES-1..3 | Seguridad/Alarma | `/v1/alarm/events*`, `/alarm/devices`, `/alarm/authorizations/{token}` | 1–2 |
| I-1/2, EI-1/2 | Internet | `/v1/internet/{id}/status|usage` | 1–2 |
| EF-1..5 | Flotilla | `/v1/gps/units*`, `/share`, `/gps/alerts|reports` | 2–3 |
| F-1..4, EB-1..3 | Facturación | `/v1/billing/*`, `/billing/cfdi/bulk` | 1 |
| S-7 | Equipos/Mant. | `/v1/equipment*`, `/maintenance/*` | 2 |
| SP-1..5, ESU-1..3 | Soporte | `/v1/tickets*`, `/tracking`, `/messages`, `/survey` | 1–2 |
| N-1, EN/EAD-4 | Notificaciones | `/v1/notifications*`, `/me/devices` | 1 |
| MC-6 | Sugerencias | `/v1/suggestions` | 1 |
| EAD-1..3 | Administración | `/v1/org/users|sites`, `/contracts*` | 1–2 |
| CCTV/Acceso | Placeholder | — | 5+ |

---

## 7. Dependencias técnicas globales y deuda en paralelo

- **Bloqueador (Fase 0):** record rules + borrar código muerto (`sentinela_contract_builder`, `syscom.import.queue`).
- **En paralelo (Fases 1–2, NO bloquean v1 read-only):** wrappers resilientes de integraciones (matar `except:pass` en `subscription.py`, `senticar_service.py`, `alarm_event.py`, `fsm_order.py`); split del god-object `subscription.py` (4 clases→archivos); suite de tests mínima (hoy 0); documentar estado de crones (freeze de facturación).
- **Integraciones (drivers):** MikroTik, Traccar/SentiCar, floLIVE, Prodigia, Messaging (EvoApi/Chatwoot). Riesgo: fallos silenciosos → la API debe degradar elegante y exponer "última info conocida".
- **Datos:** 43% de subs sin teléfono → impacta login OTP (campaña de captura en paralelo).

---

## 8. Plan de Fase 0 (detalle de arranque)

1. **Record rules de portal** en `sentinela_api/security/` para `sentinela.subscription`, `sentinela.alarm.event`, `sentinela.sign.document` (+ revisar `account.move`, `fsm.order`, `monitoring.device`). Dominio base: `[('partner_id','=',user.partner_id.id)]` / `child_of` para sucursales.
2. **Borrar código muerto:** `sentinela_contract_builder/`, `syscom.import.queue`.
3. **Esqueleto `sentinela_api`:** manifest, estructura serializers/controllers/security, service account, primer recurso `GET /v1/me`.
4. **Gateway FastAPI:** `portal_identity`, OTP WhatsApp (driver messaging), JWT+refresh, `find_partner_by_phone` portado; `GET /v1/config/theme`.
5. **SPA shell:** login (OTP/biométrico), layout, consumo de `/v1/me` y `/v1/config/theme`.
6. **Drivers (Fase 0.5):** envolver integraciones tras interfaz con retry/logging.
- **Criterio de salida Fase 0:** un cliente entra con WhatsApp, ve su perfil; ningún recurso expone datos de otro cliente (record rules verificadas).

---

## 9. Pendientes técnicos (a resolver al entrar a dev)
- Confirmar dónde viven `account.move`/`fsm.order`/`monitoring.device` record rules (algunos ya tienen reglas parciales — revisar antes de duplicar).
- Estrategia de caché (Redis dedicado vs in-memory del gateway).
- Mecanismo de roles data-driven (tabla de roles/scopes en gateway).
- Acceso a TimescaleDB de netwatch (credenciales por env vs endpoint nuevo).
- Nombre del producto / dominios (`portal.sentinela.mx`, `api.sentinela.mx`).
