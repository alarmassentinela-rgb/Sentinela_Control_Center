# Sprint 0 — Cimientos técnicos · Portal COC Sentinela

> Plan detallado previo a codificar. Referencias: `PRD_PORTAL_COC_SENTINELA.md`, `DOC_TECNICO_IMPLEMENTACION_COC.md`.
> Metodología por Sprints. Estructura: Objetivo · Alcance · Tareas/Orden/Complejidad · Entregables · Dependencias · Riesgos · Casos de prueba · Criterios de aceptación · Documentación · Rollback.
> Versión 1.0 · 2026-06-25.

## Escala de complejidad
`XS` ≈ ½ día (1 pt) · `S` ≈ 1 día (2 pts) · `M` ≈ 2–3 días (3–5 pts) · `L` ≈ 4–5 días (8 pts). **Total estimado: ~60–75 pts (≈ 3.5–4 semanas, 1 dev)** (incluye WS-7 pruebas y WS-8 observabilidad desde el inicio).

---

## 1. Objetivo
Construir los **cimientos técnicos y de seguridad** del Portal: dejar Odoo seguro para exponer datos por cliente, eliminar deuda muerta, levantar el esqueleto de `sentinela_api`, la base del Gateway de autenticación (OTP WhatsApp + JWT) y la configuración del proyecto. **Criterio de éxito:** un cliente entra con su WhatsApp y ve su perfil (`/v1/me`), sin que ningún recurso exponga datos de otro cliente.

## 2. Alcance

**DENTRO de Sprint 0:**
- Higiene: eliminar `sentinela_contract_builder` y `syscom.import.queue`; documentar estado de crones.
- Seguridad Odoo: estrategia de **Usuarios Portal**, **Record Rules**, **ACL**, scope por partner (y base de scope por sucursal).
- Auditoría de acceso (login, OTP, acceso a recursos sensibles).
- `sentinela_api`: esqueleto + capa base REST + `GET /v1/me` + `GET /v1/config/theme`.
- Gateway: scaffold, `portal_identity`, OTP WhatsApp, JWT/refresh, handshake con Odoo.
- Config del proyecto: estructura de repos (monorepo), entorno/secretos, dominios, CI básico.
- **Pruebas automatizadas desde el inicio** (unitarias, integración, seguridad, smoke).
- **Documentación y observabilidad desde el inicio** (OpenAPI/Swagger, logging estructurado, trazabilidad, monitoreo).

**FUERA de Sprint 0 (Sprint 1+):**
- Recursos de negocio (servicios, facturación, eventos, tickets…). Solo `/v1/me` y `/theme` como prueba end-to-end.
- SPA completa (solo shell de login opcional como stretch).
- Drivers de integración completos (solo el de mensajería para OTP; el resto = Sprint 0.5/1).

---

## 3. Tareas técnicas, orden y complejidad

### WS-1 · Higiene / código obsoleto
| ID | Tarea | Complej. | Dep. |
|---|---|---|---|
| T1.1 | Verificar 0 referencias y **eliminar `sentinela_contract_builder/`** | XS | — |
| T1.2 | Eliminar modelo roto **`syscom.import.queue`** (modelo + import en `__init__` + línea ACL huérfana) | S | — |
| T1.3 | `CRON_STATUS.md`: documentar crones activos/congelados (freeze facturación) | XS | — |

### WS-2 · Seguridad Odoo (el bloqueador)
| ID | Tarea | Complej. | Dep. |
|---|---|---|---|
| T2.0 | **Decisión técnica: patrón de Usuarios Portal y scoping** (ver §12) | S | — |
| T2.1 | Auditar reglas existentes (`monitoring.device` 2 rules, `fsm.order` 3 rules) para NO duplicar | S | — |
| T2.2 | Grupo de seguridad **Portal Cliente** + estrategia de usuario portal (lazy por partner en primer login) | M | T2.0 |
| T2.3 | Record rule `sentinela.subscription` (partner / child_of sucursal) | S | T2.2 |
| T2.4 | Record rule `sentinela.alarm.event` (partner) | S | T2.2 |
| T2.5 | Record rule `sentinela.sign.document` (partner) | S | T2.2 |
| T2.6 | Revisar/añadir record rule `account.move` (out_invoice del partner) — **delicado** (reglas core) | M | T2.2 |
| T2.7 | Extender rules `fsm.order`/`monitoring.device` para acceso de cliente portal | S | T2.2 |
| T2.8 | **ACL** (`ir.model.access.csv`) read-only del grupo portal en modelos expuestos | S | T2.2 |
| T2.9 | Base de **scope por sucursal**: dominio `service_address_id child_of` + cómo el API lo aplica sobre el techo de la record rule | M | T2.3 |

### WS-3 · Auditoría
| ID | Tarea | Complej. | Dep. |
|---|---|---|---|
| T3.1 | Registro de **auditoría de acceso** (cliente, recurso, IP, timestamp) — log estructurado en gateway + opcional modelo en Odoo | M | T5.1 |
| T3.2 | Auditoría de **eventos sensibles** (login, OTP fallido/ok, firma, autorización) | S | T5.4 |

### WS-4 · `sentinela_api` (esqueleto)
| ID | Tarea | Complej. | Dep. |
|---|---|---|---|
| T4.1 | Crear addon: `__manifest__` (depends base/mail/portal/subscriptions/monitoring/fsm/cfdi/digital_sign), estructura `controllers/serializers/security/` | S | — |
| T4.2 | **Capa base REST**: auth service-account, errores RFC-7807, paginación, **helper central de scoping** (filtro obligatorio por partner) | M | T4.1, T2.9 |
| T4.3 | Recurso `GET /v1/me` (perfil del partner, serializado) | S | T4.2 |
| T4.4 | `GET /v1/config/theme` (branding desde config — costura) | S | T4.2 |
| T4.5 | Convención de **serializadores/DTO base** | S | T4.2 |
| T4.6 | Release a **STAGING** (`Sentinela_STAGING`) vía skills release/deploy | S | T4.3 |

### WS-5 · Gateway de autenticación (base)
| ID | Tarea | Complej. | Dep. |
|---|---|---|---|
| T5.1 | Scaffold FastAPI + Docker + estructura (config/env/logging) | S | T6.2 |
| T5.2 | Store `portal_identity` (Postgres del gateway): teléfono/email→partner_id | S | T5.1 |
| T5.3 | **Driver de mensajería WhatsApp (OTP)**: interfaz + impl. EvoApi (canal transaccional separado) | M | T5.1 |
| T5.4 | Flujo **OTP** request/verify + rate-limit + bloqueo por intentos | M | T5.2, T5.3 |
| T5.5 | **JWT** + refresh + contraseña (argon2) + biométrico (registro de credencial) | M | T5.2 |
| T5.6 | `find_partner_by_phone` (portar patrón de `chatwoot_bot/odoo.py`, llamar vía `sentinela_api`) | S | T5.2, T4.3 |
| T5.7 | **Handshake gateway↔Odoo**: service account + paso firmado de `partner_id`/scopes | M | T4.2 |
| T5.8 | Endpoints `/v1/auth/*` + `/v1/me` (passthrough con scope) | M | T5.5, T5.7 |
| T5.9 | Deploy gateway al server (rsync + `docker compose up -d --build`) | S | T5.8 |

### WS-6 · Configuración inicial del proyecto
| ID | Tarea | Complej. | Dep. |
|---|---|---|---|
| T6.1 | Estructura de repos (gateway + SPA): decisión mono-repo vs repos | S | — |
| T6.2 | Entorno/secretos (vault o env) + dominios (`api.sentinela.mx`, `portal.sentinela.mx`) + Cloudflare/NPM | S | — |
| T6.3 | CI/lint básico + convenciones de commit/branch | S | T6.1 |
| T6.4 | (Stretch) SPA shell mínimo: login OTP + consumo `/v1/me` + `/theme` | M | T5.8, T4.4 |

### WS-7 · Estrategia de pruebas automatizadas (desde el inicio)
| ID | Tarea | Complej. | Dep. |
|---|---|---|---|
| T7.1 | Framework tests Odoo (`TransactionCase`) en `sentinela_api/tests/` + runner | S | T4.1 |
| T7.2 | **Tests de seguridad** automatizados (aislamiento por partner: TC-S1..S4) | M | T2.x |
| T7.3 | Tests unitarios del gateway (pytest): identidad, OTP, JWT | M | T5.x |
| T7.4 | Tests de integración gateway↔`sentinela_api` (`/v1/me` end-to-end) | M | T5.8 |
| T7.5 | **Smoke tests** post-deploy (health + login + `/me`) | S | T5.9 |
| T7.6 | Integrar tests al CI (pipeline falla si rojo) | S | T6.3, T7.1 |

### WS-8 · Documentación y observabilidad (desde el inicio)
| ID | Tarea | Complej. | Dep. |
|---|---|---|---|
| T8.1 | **OpenAPI/Swagger** del gateway (FastAPI auto, esquema versionado `/v1`) | S | T5.1 |
| T8.2 | **Logging estructurado (JSON)** en gateway y `sentinela_api` con `request_id` de correlación | M | T5.1 |
| T8.3 | **Trazabilidad** request→Odoo (propagar `request_id`/trace en el handshake) | M | T5.7, T8.2 |
| T8.4 | **Métricas + healthchecks** (`/health`, `/metrics`) + monitoreo básico (uptime/alertas) | M | T5.1 |
| T8.5 | Conectar auditoría (WS-3) al logging estructurado | S | T3.1, T8.2 |

---

## 4. Orden recomendado de implementación

```
Bloque A (paralelo, sin deps)     → T1.1 T1.2 T1.3 · T6.1 T6.2 T6.3 · T4.1 · T2.0 T2.1
Bloque B (seguridad Odoo)         → T2.2 → T2.3 T2.4 T2.5 T2.7 T2.8 → T2.6 → T2.9
Bloque C (API base)               → T4.2 (tras T2.9) → T4.3 T4.4 T4.5 → T4.6 (deploy STAGING)
Bloque D (gateway)                → T5.1 T5.2 → T5.3 → T5.4 T5.5 → T5.6 T5.7 → T5.8 → T5.9
Bloque E (auditoría, transversal) → T3.1 (con T5.1) · T3.2 (con T5.4)
Bloque F (stretch)                → T6.4
```
**Ruta crítica:** T2.0 → T2.2 → T2.9 → T4.2 → T5.7 → T5.8 → `/v1/me` end-to-end. Higiene (WS-1) y config (WS-6) corren en paralelo desde el día 1.

---

## 5. Entregables
- `sentinela_contract_builder` y `syscom.import.queue` eliminados; `CRON_STATUS.md`.
- Grupo Portal + Record Rules + ACL desplegados en STAGING (y verificados).
- Addon `sentinela_api` instalable con `/v1/me` y `/v1/config/theme` funcionando.
- Gateway con OTP WhatsApp + JWT + `/v1/auth/*` desplegado.
- Auditoría de acceso operando (logs).
- Repos, entorno, dominios y CI configurados.
- Documentación técnica (ver §10).

## 6. Dependencias
- **Internas:** credenciales service-account Odoo; acceso STAGING (`:8075`); credenciales EvoApi (canal OTP); `ir.config_parameter` para secretos.
- **Externas:** EvoApi (WhatsApp) disponible y con plantilla/sesión para OTP; Cloudflare/NPM para dominios; Postgres para el gateway.
- **De decisión:** §12 resuelto antes de T2.2 y T6.1.

## 7. Riesgos y mitigación
| Riesgo | Sev. | Mitigación |
|---|---|---|
| Record rules mal definidas → fuga de datos o bloqueo de operación interna | 🔴 | Probar con usuario portal real en STAGING; rules con `[(1,'=',1)]` para grupos internos; pruebas negativas (T8). |
| `account.move` rules chocan con reglas core de Odoo | 🟠 | Extender, no reemplazar; probar emisión/cobranza interna tras el cambio. |
| Crecimiento de `res.users` (usuario portal por partner) | 🟡 | Creación **lazy** (solo en primer login); sin costo de licencia en Community; monitorear performance. |
| EvoApi/WhatsApp no apto para OTP (plantillas/sesión) | 🟠 | Validar early (T5.3); fallback contraseña; SMS como plan B futuro. |
| Eliminar código "muerto" que algo usaba | 🟡 | `grep` de referencias + correr `-u` en STAGING antes de prod. |
| Deploy: server no es git tree (rsync) | 🟡 | Usar skills `release-modulo`/`deploy-modulo`; verificar `-u` en STAGING antes de V18. |
| Handshake gateway↔Odoo inseguro (suplantar partner_id) | 🟠 | Firmar el `partner_id`; validar en `sentinela_api`; service account de permisos mínimos. |

## 8. Casos de prueba
**Seguridad (críticos):**
- TC-S1: cliente A NO ve subs/eventos/facturas/documentos de cliente B (pruebas negativas por modelo).
- TC-S2: cliente con sucursales solo ve las de su `sucursal_ids`.
- TC-S3: usuario interno (operador/admin) conserva acceso completo (no regresión).
- TC-S4: ACL read-only — el portal NO puede escribir donde no debe.
**Auth:**
- TC-A1: OTP correcto → JWT válido; OTP incorrecto/expirado → rechazo; N intentos → bloqueo + rate-limit.
- TC-A2: refresh token rota; logout invalida.
- TC-A3: teléfono no registrado → mensaje neutro (no filtra existencia).
**API:**
- TC-P1: `GET /v1/me` devuelve solo datos del partner autenticado.
- TC-P2: `GET /v1/config/theme` público devuelve branding sin datos sensibles.
- TC-P3: errores en formato RFC-7807; paginación correcta.
**Higiene:**
- TC-H1: `-u` de todos los módulos en STAGING sin errores tras eliminar código muerto.
**Auditoría:**
- TC-AU1: cada acceso/login/firma genera registro con cliente+IP+timestamp.

## 9. Criterios de aceptación (Definition of Done)
- ✅ Record rules + ACL desplegados; **TC-S1..S4 pasan** en STAGING.
- ✅ `sentinela_api` instalado; `/v1/me` y `/v1/config/theme` responden con scope correcto.
- ✅ Gateway: OTP WhatsApp end-to-end + JWT; **TC-A1..A3 pasan**.
- ✅ Flujo completo: login WhatsApp → JWT → `/v1/me` con datos propios.
- ✅ Auditoría registrando; código muerto eliminado; `-u` limpio.
- ✅ Documentación §10 entregada; sin secretos en repo.
- ✅ Probado en STAGING; **no desplegar a V18 hasta validación** (o desplegar solo lo no disruptivo: addon nuevo + rules verificadas).
- ✅ **Pruebas automatizadas** corriendo en CI (unitarias + seguridad + integración + smoke); pipeline en verde.
- ✅ **Observabilidad activa:** OpenAPI/Swagger publicado, logging estructurado con `request_id`, healthchecks y monitoreo básico.

## 10. Documentación técnica a producir
- `sentinela_api/README.md` (estructura, convenciones de serializador/scoping, cómo añadir un recurso).
- Gateway `README.md` (arquitectura, env, OTP, JWT, despliegue).
- `SECURITY_PORTAL.md` (modelo de usuarios portal, record rules, ACL, scope sucursal, auditoría).
- `CRON_STATUS.md` (estado de crones).
- Actualizar `CLAUDE.md` raíz (nuevo módulo + apps standalone del COC).

## 11. Plan de rollback
- **Record rules/ACL:** versionadas en `sentinela_api`; rollback = revertir commit + `-u`. En STAGING primero; si rompen operación interna, desinstalar/deshabilitar las `ir.rule` del grupo portal (no afecta datos).
- **Addon `sentinela_api`:** es nuevo y aislado; rollback = desinstalar módulo (no toca datos de negocio).
- **Eliminación de código muerto:** está en git; rollback = revertir commit. Verificado en STAGING antes de prod.
- **Gateway/SPA (Docker):** despliegue por imagen; rollback = `docker compose` a imagen anterior (tag previo). Stateless → sin migración de datos (salvo `portal_identity`, con respaldo).
- **Regla de oro:** todo cambio Odoo se valida en `Sentinela_STAGING` antes de `V18`.

## 12. Decisiones técnicas (RESUELTAS · aprobadas 25-jun)
1. ✅ **Usuarios Portal / scoping: Opción A.** Creación **lazy** del usuario portal en el primer login, vinculado al `res.partner`. **Las Record Rules de Odoo son la PRIMERA línea de defensa** del aislamiento entre clientes; la lógica del Gateway nunca las sustituye, solo las complementa.
2. ✅ **Monorepo** (gateway + SPA + infra juntos).
3. ✅ **Dominios separados:** Portal (`portal.sentinela.mx`) y API (`api.sentinela.mx`).
4. ✅ **Almacén independiente** para datos propios del Gateway (`portal_identity`/OTP/sesiones).
5. ✅ **Despliegue STAGING primero**; a producción solo cuando se cumplan TODOS los criterios de aceptación y las pruebas de seguridad.
6. ✅ **(Nuevo) Pruebas automatizadas desde el inicio** (WS-7) y **observabilidad/documentación desde el inicio** (WS-8).
