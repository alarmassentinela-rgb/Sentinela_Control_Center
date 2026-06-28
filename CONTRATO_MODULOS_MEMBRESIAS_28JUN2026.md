# Contrato de Integración — Módulo de Membresías (`sentinela_subscriptions`)

**Versión del contrato:** `1.0` · 28-jun-2026 · **Estado del módulo:** 🧊 congelado.
Define la **interfaz pública estable** que Membresías ofrece al resto del ERP (Motor de Catálogo, Portal, app, IA, CRM, etc.). El objetivo: que **ningún otro módulo conozca la implementación interna** de Membresías. La comunicación se hace **solo** por la superficie pública aquí declarada.

> Este documento **describe la superficie pública que YA existe** (no agrega código al módulo congelado). Si en el futuro se requiere glue nuevo (p. ej. emisión de eventos), se hará en un **módulo puente separado** —nunca modificando Membresías— por fases, en STAGING y aprobado.

---

## 1. Principio rector
- **Membresías no depende de nadie nuevo**, y **nadie depende de Membresías** salvo por esta interfaz.
- **El único modelo compartido es `product.template`** (ambos dependen de `product`). Los *planes* de membresía son productos **propios**.
- **Dirección de dependencias prohibida:** `product_catalog_engine` / conectores **NO** pueden `depends` de `sentinela_subscriptions`, ni viceversa.

## 2. Superficie PÚBLICA (estable — se puede consumir)
### 2.1 Modelo `sentinela.subscription` — **solo lectura** para externos
Campos estables (no cambiarán sin versionar el contrato):
| Campo | Tipo | Significado |
|---|---|---|
| `name` | Char | Folio `SUB-####`. |
| `partner_id` | M2o res.partner | Cliente. |
| `product_id` | M2o product.template | Plan contratado. |
| `service_address_id` | M2o res.partner | Sucursal/dirección de servicio. |
| `state` | Selection | Estado comercial (`draft…active…cancelled`). |
| `technical_state` | Selection | Estado de red (`active/suspended/cut`). |
| `billing_mode` | Selection | `normal` / `courtesy`. |
| `next_billing_date` | Date | Próximo cobro. |
| `recurring_interval` | Int | Meses del ciclo. |
| `price_unit` | Monetary | Precio del periodo. |

### 2.2 Vínculo factura ↔ suscripción (lectura)
- `account.move.subscription_id` (1) y `account.move.subscription_ids` (M2M, facturas agrupadas).

### 2.3 API REST (canal externo preferente)
- A través de **`sentinela_api`** (Portal COC): endpoints REST/JSON de consulta de "Mis Servicios" / facturación. **Es el canal recomendado** para Portal, app, IA y sistemas de Alea (no acceder al ORM interno).

## 3. Superficie INTERNA (PROHIBIDO depender de ella)
No forman parte del contrato y **pueden cambiar sin aviso**:
- Generación de facturas: `_cron_generate_pre_invoices`, `_billing_generate_invoice`, `_billing_period_label`, lógica anti-duplicado.
- Overrides de `account.move`/`sale.order` (cobro adelantado: `_advance_*`, `action_post`).
- Provisioning: `mikrotik_profile`, `router`, `flolive_service`, `senticar_service`, `gps_device`, matriz de servicios, walled-garden, SSH.
- Crones, plantillas de contrato, secuencias, parámetros internos.

> Si necesitas algo que hoy solo existe como método interno, **se solicita exponerlo en el contrato** (con versión), no se llama directamente.

## 4. Reglas para el Motor de Catálogo (convivencia)
1. **El Catálogo solo gestiona productos con proveedor-distribuidor** (`product.supplierinfo` de un `distributor.backend`). Los **planes de membresía son productos propios** → **fuera** del alcance de sincronización/promoción/limpieza del Catálogo.
2. **Criterio de "producto propio":** `product.template` **sin** `supplierinfo` ligado a un distribuidor del Catálogo (o marcado explícitamente como propio/servicio). El scheduler y la limpieza del Catálogo **deben excluirlos** por diseño.
3. El Catálogo **no lee ni escribe** `sentinela.subscription`. Si en el futuro un plan debe "consumir" un producto de distribuidor (p. ej. un kit), se hace vía `product.template`/`supplierinfo`, no vía acoplamiento de código.

## 5. Eventos (futuro, opcional — no se implementa ahora)
Si se requiere reactividad (notificar a Portal/IA/CRM cuando algo cambia), se publicarán eventos **desde un módulo puente** que observe Membresías (sin modificarlo), reutilizando el **bus de eventos del Catalog Engine** (`catalog.event`/`EventBus`) o `bus.bus`. Eventos candidatos (nombres reservados):
`SubscriptionActivated`, `SubscriptionSuspended`, `SubscriptionReactivated`, `SubscriptionCancelled`, `SubscriptionInvoiced`, `PlanChanged`.
**Hoy:** no existen; los consumidores usan **consulta** (API/lectura de modelos públicos), no eventos.

## 6. Versionado y cambios del contrato
- La **superficie pública (§2) es estable**. Cambios incompatibles ⇒ **subir versión del contrato** (`1.0 → 2.0`) + periodo de **deprecación** documentado.
- Agregar campos/endpoints nuevos (compatible) ⇒ `1.0 → 1.1`.
- Los consumidores se programan **contra esta versión**, no contra internals.

## 7. Cumplimiento (cómo lo verificamos)
- **Revisión de `depends`:** ningún módulo nuevo agrega `sentinela_subscriptions` a sus dependencias (ni Membresías agrega las de otros).
- **Revisión de imports:** el Catálogo no importa `odoo.addons.sentinela_subscriptions.*`.
- **Filtro de propios en el Catálogo:** prueba que el scheduler/limpieza excluye productos sin distribuidor.

---

> **Resumen:** Membresías queda **estable y desacoplada**. El resto del ERP la consume por (a) `product.template` compartido, (b) campos públicos de solo lectura de `sentinela.subscription`, y (c) la API REST de `sentinela_api`. Sus internals quedan **fuera de límites**. El Motor de Catálogo y Membresías **no se conocen entre sí**.
