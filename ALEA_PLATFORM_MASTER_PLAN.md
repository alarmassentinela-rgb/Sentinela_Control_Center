# ALEA PLATFORM — Master Plan (brújula del ecosistema)

**Alea Systems** · **v2** · 28-jun-2026 · Documento maestro y **única fuente de verdad** del ecosistema.
Define **dónde vive cada componente**, **cómo interactúan**, las **reglas de gobernanza** y **qué es
activo estratégico vs. reemplazable**. Toda pieza nueva se ubica primero en este mapa.

---

## 0. Regla de gobernanza (obligatoria)
**Ningún desarrollo importante comienza sin responder tres preguntas:**
1. **¿Qué problema de negocio resuelve?**
2. **¿Dónde encaja dentro de Alea Platform?** (capa + componente)
3. **¿Puede reutilizar un componente existente antes de crear uno nuevo?**

Principios de plataforma (innegociables):
- **Las CAPACIDADES se comunican entre capacidades; las APLICACIONES solo orquestan experiencias.** La lógica de negocio vive en las capacidades, nunca en las apps.
- **Lenguaje de negocio + puertos/adaptadores:** se describe lo que cada capacidad *hace* ("Catálogo consulta", "Eventos publican", "Pagos autorizan"); los proveedores son **adaptadores reemplazables**, no parte del contrato.
- **Una sola fuente de verdad por dato;** prohibido duplicar lógica. Extender antes que reemplazar. ADR para cambios importantes.

---

## 1. Mapa de la plataforma
```
Alea Platform
├── Core (CAPACIDADES reutilizables, agnósticas de negocio)
│   ├── Alea API Gateway          🛠️ PUNTO ÚNICO DE ACCESO  [FastAPI; eleva el BFF del Portal]  ← auth/caché/agregación/observabilidad; SIN lógica de negocio
│   ├── Plataforma de Eventos     🔜 NUEVA · ESTRATÉGICA     ← MEMORIA HISTÓRICA + sistema nervioso; Event Store PROPIO (Odoo/SentiCar/Netwatch/FSM/Gateway = productores)
│   ├── Catalog Engine            ✅ v1.0 LTS · ESTRATÉGICA  ← capacidad "CATÁLOGO" (multi-distribuidor, AI-ready)  [distributor_connector_base + product_catalog_engine + distributor_*]
│   ├── Membership Engine         ✅ PROD (congelado) · ESTRATÉGICA  [sentinela_subscriptions]  (facturación recurrente + provisioning)
│   └── Public APIs (tras el Gateway)  ✅/🟡  Catalog Public Interface v1 + ERP API (sentinela_api)
│
├── Business Apps (cara al usuario — solo ORQUESTAN capacidades)
│   ├── ERP Sentinela             ✅ PROD                   [Odoo 18 + módulos sentinela_*]  (sistema de registro)
│   ├── Portal de Clientes (COC)  🛠️ en desarrollo          ← **1er consumidor de Catalog Engine y de la Plataforma de Eventos**
│   ├── App Móvil                 🔜 futuro                 (mismas capacidades/APIs)
│   └── Portal de Distribuidores  🔜 futuro                 (mismas capacidades/APIs)
│
├── Operations (operación del negocio — productores de eventos)
│   ├── Monitoring                ✅ PROD                   [sentinela_monitoring]  (central de alarmas)
│   ├── Dispatch / FSM            ✅ PROD                   [sentinela_fsm]  (órdenes de campo)
│   └── GPS / Tracking            ✅ PROD                   [SentiCar (marca) sobre Traccar (motor)]
│
├── Intelligence (datos / IA — CONSUMEN la Plataforma de Eventos)
│   ├── SentiBot / IA del Cliente 🔜 futuro                 ← interfaz inteligente; grounded en la memoria de eventos
│   ├── Analytics                 🔜 futuro
│   └── AI Services               🔜 futuro                 (Catalog ya es "AI-ready": ai_*, eventos, API)
│
└── Integrations (proveedores externos — ADAPTADORES reemplazables)
    ├── Distribuidores: Syscom ✅ (referencia) · CT/CVA/Exel/Ingram/Intcomex/Tecnosinergia/TVC 🔜  (un conector c/u, sin tocar el núcleo)
    └── Servicios: Stripe (pago) · EvoApi (WhatsApp) · floLIVE (SIM) · Prodigia (PAC CFDI) · Securithor (legacy saliente)
```
Leyenda: ✅ estable · 🟡 parcial · 🛠️ en desarrollo · 🔜 futuro.

## 2. Componentes y responsabilidad
| Componente | Capa | Responsabilidad | Estado |
|---|---|---|---|
| **Alea API Gateway** | Core | Punto único de acceso: auth/authz/caché/agregación/observabilidad. **Sin lógica de negocio.** | 🛠️ |
| **Plataforma de Eventos** | Core | Memoria histórica + distribución de eventos a consumidores (notificaciones, IA, auditoría, analítica). | 🔜 |
| **Catalog Engine — capacidad "Catálogo"** | Core | Productos, categorías, atributos, imágenes, fichas técnicas, compatibilidades, disponibilidad, precios, promociones, equivalencias, búsqueda semántica, recomendaciones para IA. **El consumidor solo "Consulta Catálogo"; nunca conoce a Syscom/Ingram/etc.** | ✅ v1.0 LTS |
| **Membership Engine** | Core | Facturación recurrente + provisioning (internet/alarma/GPS). | ✅ PROD |
| **Public API** | Core | Contratos HTTP estables: Catalog `/catalog/api/v1` + ERP `sentinela_api`. | ✅/🟡 |
| **ERP Sentinela** | Apps | Sistema de registro (clientes, contabilidad, CFDI, inventario). | ✅ PROD |
| **Portal de Clientes (COC)** | Apps | Autoservicio del cliente (Estado de Tranquilidad + cuenta + **catálogo**). 1er consumidor de Catalog y Eventos. | 🛠️ |
| **Monitoring / FSM / GPS** | Operations | Alarmas, despacho, rastreo. Productores de eventos. | ✅ PROD |
| **SentiBot / IA** | Intelligence | Interfaz inteligente; consume la memoria de eventos. | 🔜 |
| **Integrations** | Integrations | Conectores de distribuidores y servicios (adaptadores). | ✅ Syscom; resto 🔜 |

## 3. Contratos de interacción
> **Objetivo:** todos los consumidores (Portal, App, Distribuidores, IA, integraciones, dashboards, internas) → **Alea API Gateway** (punto único). Adopción **incremental** (ver `POLITICA_EVOLUCION_PORTAL_28JUN2026.md`); hoy las features consumen contratos públicos (Catalog v1 / ERP API) y el Gateway se intercala cuando aporte valor, **sin frenar el Portal**.
- **Capacidades hablan con capacidades; apps solo orquestan.** Ningún consumidor habla directo con un motor ni con Odoo: habla con **capacidades** vía contrato.
- **Consultar Catálogo:** apps → Catalog Public Interface v1 (credencial de servicio; nunca el ORM). El catálogo **abstrae a todos los distribuidores**.
- **Eventos:** los **productores publican** (Odoo, SentiCar, Netwatch, FSM, Gateway); los **consumidores consumen** (Notificaciones, IA, Auditoría, Analytics, Timeline del Portal). Event Store **propio**.
- **Gateway → ERP** por `sentinela_api` (propaga la auth del cliente): contratos/membresías/facturas/tickets/OS/dispositivos/eventos.
- **Catalog ↔ Membership:** independientes; comparten solo `product.template`; el Catalog excluye productos propios (planes).
- **Patrón columna vertebral:** comandos **síncronos**; consecuencias por **eventos**.
- **Regla de dependencias:** todo por API/contrato; prohibido el acoplamiento de código entre capas.

## 4. Activos estratégicos vs. reemplazables (qué proteger como IP)
**🏆 Activos estratégicos (ventaja competitiva — propiedad intelectual de Sentinela/Alea):**
Estado de Tranquilidad · Plataforma de Eventos · **Catalog Engine** · Membership Engine · SentiBot ·
Seguridad en Vivo · **Modelo de Capacidades** (la plataforma misma → habilita white-label) · SentiCar (marca/experiencia).

**🔌 Reemplazable mediante adaptadores (infraestructura/proveedores; commodities):**
Alea API Gateway · Odoo/ERP (sistema de registro, sustituible con esfuerzo) · Monitoring · Netwatch ·
FSM · **Traccar** (motor GPS) · Stripe · EvoApi · floLIVE · Prodigia · Securithor · Syscom y demás distribuidores.

> Criterio: es **estratégico** si encarna la experiencia (tranquilidad), los **datos** (eventos/relación
> del cliente), la **inteligencia** (IA grounded) o el **modelo reutilizable**. Es **reemplazable** si es
> un motor genérico detrás de un puerto/adaptador. Decisión de negocio: **invertir y proteger** lo
> estratégico; **no casarse** con lo reemplazable.

## 5. Estado por madurez (al 28-jun-2026)
- **Estable/congelado:** Catalog Engine v1.0 LTS, Membership Engine, Monitoring/FSM/GPS (PROD).
- **En desarrollo:** Portal de Clientes (Sprint 1 en UAT; integrándose con Catalog Engine — ver `BLUEPRINT_INTEGRACION_PORTAL_CATALOG_ENGINE`).
- **Diseño/próximo:** Plataforma de Eventos (capacidad Core nueva), SentiBot/IA, App Móvil, Portal de Distribuidores, Analytics.

## 6. Cómo usar este documento
Ante cualquier idea nueva: ubicarla en el **mapa (§1)**, responder las **3 preguntas (§0)** y revisar si
un **componente Core** ya la cubre. Si nace un módulo, se agrega aquí con su capa, responsabilidad,
contratos y clasificación estratégica.

> **Reconciliación de vistas:** `ARQUITECTURA_ECOSISTEMA_COC.md` (vista de **capacidades**: Identidad,
> Eventos, Estado, Notificaciones, Pagos, Documentos, Catálogo, …) es un **refinamiento** de este mapa
> de capas, **subordinado a esta brújula**. No es una arquitectura paralela: misma realidad, distinto zoom.
> Documentos relacionados: `ESPECIFICACION_MOTOR_CATALOGO_v1.0`, `BLUEPRINT_INTEGRACION_PORTAL_CATALOG_ENGINE`,
> `BLUEPRINT_ALEA_API_GATEWAY`, `producto/PRODUCT_VISION.md` + `producto/PROD_0x`, `PRD_PORTAL_COC_SENTINELA.md`.
