# ALEA PLATFORM — Master Plan (brújula del ecosistema)

**Alea Systems** · v1 · 28-jun-2026 · Documento maestro. Define **dónde vive cada componente**, **cómo interactúan** y las **reglas de gobernanza**. Toda pieza nueva se ubica primero en este mapa.

---

## 0. Regla de gobernanza (obligatoria)
**Ningún desarrollo importante comienza sin responder tres preguntas:**
1. **¿Qué problema de negocio resuelve?**
2. **¿Dónde encaja dentro de Alea Platform?** (capa + componente)
3. **¿Puede reutilizar un componente existente antes de crear uno nuevo?**

Complementa la **Filosofía de Evolución** del Catalog Engine (no romper compat pública · extender antes que reemplazar · medir antes de optimizar · no duplicar lógica · ADR para cambios importantes). Objetivo: que la plataforma crezca como **ecosistema ordenado**, no como módulos aislados.

---

## 1. Mapa de la plataforma
```
Alea Platform
├── Core (componentes reutilizables, agnósticos de negocio)
│   ├── Catalog Engine            ✅ v1.0 LTS (congelado)   [distributor_connector_base + product_catalog_engine + distributor_*]
│   ├── Membership Engine         ✅ en PROD (congelado)    [sentinela_subscriptions]  (facturación recurrente + provisioning)
│   └── Public API                ✅/🟡  Catalog Public Interface v1 + ERP API (sentinela_api)
│
├── Business Apps (cara al usuario)
│   ├── ERP Sentinela             ✅ PROD                   [Odoo 18 + módulos sentinela_*]
│   ├── Portal de Clientes        🛠️ en desarrollo          [Portal COC: Next.js SPA + Gateway BFF]  ← 1er consumidor del Catalog Engine
│   └── App Móvil                 🔜 futuro                 (consumirá las MISMAS APIs)
│
├── Operations (operación del negocio)
│   ├── Monitoring                ✅ PROD                   [sentinela_monitoring]  (central de alarmas)
│   ├── Dispatch / FSM            ✅ PROD                   [sentinela_fsm]  (órdenes de campo)
│   └── GPS / Tracking            ✅ PROD                   [SentiCar/Traccar + GPS en sentinela_subscriptions]
│
├── Intelligence (datos / IA)
│   ├── Analytics                 🔜 futuro
│   └── AI Services               🔜 futuro                 (el Catalog ya es "AI-ready": campos ai_*, eventos, API)
│
└── Integrations (proveedores externos)
    ├── Syscom                    ✅ conector de referencia [distributor_syscom]
    ├── CT / CVA / Exel / Ingram / Intcomex / Tecnosinergia   🔜 (un conector c/u, sin tocar el núcleo)
    └── Otros (Prodigia CFDI, floLIVE, Stripe, …)            ✅/🟡 según el caso
```
Leyenda: ✅ estable · 🟡 parcial · 🛠️ en desarrollo · 🔜 futuro.

## 2. Componentes y responsabilidad (resumen)
| Componente | Capa | Responsabilidad | Estado |
|---|---|---|---|
| **Catalog Engine** | Core | Catálogo multi-distribuidor: índice, frescura, promoción a producto maestro, conectores | ✅ v1.0 LTS (STAGING) |
| **Membership Engine** | Core | Facturación recurrente + provisioning (internet/alarma/GPS) | ✅ PROD (congelado) |
| **Public API** | Core | Contratos HTTP estables: Catalog `/catalog/api/v1` + ERP `sentinela_api` | ✅/🟡 |
| **ERP Sentinela** | Apps | Sistema de registro (clientes, contabilidad, CFDI, inventario) | ✅ PROD |
| **Portal de Clientes** | Apps | Autoservicio del cliente (catálogo + su cuenta) | 🛠️ |
| **App Móvil** | Apps | Igual que el Portal, sobre las mismas APIs | 🔜 |
| **Monitoring / FSM / GPS** | Operations | Alarmas, despacho, rastreo | ✅ PROD |
| **Integrations** | Integrations | Conectores de distribuidores y servicios | ✅ Syscom; resto 🔜 |

## 3. Contratos de interacción (cómo encajan)
- **Portal/App → Catalog Engine**: solo por **Catalog Public Interface v1** (API key de servicio; nunca el ORM).
- **Portal/App → ERP**: por **`sentinela_api`** (auth por cliente) para contratos/membresías/facturas/tickets/OS/dispositivos/eventos.
- **Catalog Engine ↔ Membership Engine**: independientes; **comparten solo `product.template`**; el Catalog excluye productos propios (planes).
- **Catalog Engine → Distribuidores**: por **conectores** (`DistributorConnector`); agregar uno no toca el núcleo.
- **Operations (Monitoring/FSM/GPS)** se relacionan con el cliente por `partner_id` en el ERP.
- **Regla de dependencias:** todo por **API/contrato**; prohibido el acoplamiento de código entre capas (sin `depends` cruzados indebidos).

## 4. Estado por madurez (al 28-jun-2026)
- **Estable/congelado:** Catalog Engine v1.0 LTS, Membership Engine.
- **En desarrollo:** Portal de Clientes (integrándose con el Catalog Engine — ver `BLUEPRINT_INTEGRACION_PORTAL_CATALOG_ENGINE`).
- **Backlog próximo:** Catalog Engine v1.1 (USD→MXN, promoción por lote, hash de keys, alertas, etc.), nuevos conectores, App Móvil, Analytics/IA.

## 5. Cómo usar este documento
Ante cualquier idea nueva: ubicarla en el **mapa (§1)**, responder las **3 preguntas (§0)** y revisar si un **componente Core** ya la cubre. Si nace un módulo, se agrega a este mapa con su capa, responsabilidad y contratos.

> Documentos relacionados: `ESPECIFICACION_MOTOR_CATALOGO_v1.0_28JUN2026.md` (contrato del Catalog), `BLUEPRINT_INTEGRACION_PORTAL_CATALOG_ENGINE_28JUN2026.md`, `AUDITORIA_MEMBRESIAS_SUBSCRIPTIONS_28JUN2026.md` + `CONTRATO_MODULOS_MEMBRESIAS`, `PRD_PORTAL_COC_SENTINELA.md`.
