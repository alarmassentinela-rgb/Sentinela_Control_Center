# Sprint 2 — Vertical COBRANZA (Centro Financiero, MVP sobre la plataforma)

> Especificación **construible**. Primera vertical de negocio sobre la plataforma Alea. Entrega valor
> visible **y** hace nacer capacidades reales con el **contrato MÍNIMO** que esta vertical exige.
> Respeta `FILOSOFIA_EVOLUCION_PLATAFORMA.md`:
> **"Una capacidad no nace para reutilizarse; se reutiliza solo cuando una 2ª vertical lo demuestra."**
> Realiza el MVP de `producto/PROD_01_cobranza.md`. No toca el Sprint 1 (en UAT, congelado).

## 0. Objetivo y valor
**El cliente paga en línea y queda al corriente, sin fricción**, y lo siente en su Estado de
Tranquilidad. Acelera cobranza, baja morosidad y elimina conciliación manual.

## 1. Alcance del Sprint (in / out)
**IN:** pagar facturas (liquidación total) con **tarjeta vía Motor de Pago** · confirmación inmediata ·
**Ledger financiero mínimo** (fuente del Estado de Cuenta) · **factura pagada** · **CFDI desacoplado**
(reintetable) · **reactivación por Policy** · **Event Store mínimo** · **notificación** de confirmación
(reusa canal) · **indicadores MVP** (3 consultas). Convive con OXXO/banco.
**OUT (no se construye ahora):** **Timeline** (nace cuando una 2ª vertical consuma eventos) · pago
recurrente / medio guardado · pago parcial / planes · reembolso/disputa self-service · Dashboard Engine
· CQRS/Replay/Projections/Event Sourcing · más métodos/proveedores.

## 2. Capacidades que consume + contrato MÍNIMO exigido por Cobranza
| Capacidad | Lo MÍNIMO que Cobranza necesita ahora | Origen |
|---|---|---|
| **Identidad** | Sesión del cliente + alcance a SUS servicios/facturas | ✅ existe (Sprint 1) |
| **Ledger (financiero mínimo)** | Registrar movimientos y **servir el Estado de Cuenta** (§3) | 🆕 nace en Cobranza |
| **Pagos** | **Autorizar** intención → resultado {confirmado/en proceso/rechazado} vía **`PaymentAdapter`** | 🆕 puerto + adaptador |
| **CFDI / Documentos** | Emitir/timbrar **al consumir `factura.pagada`** (async, reintetable) | ✅ reusa timbrado existente |
| **Eventos (Event Store mínimo)** | `append()` · `read()` · `byAggregate()` — nada más (§6) | 🆕 nace mínimo |
| **Notificaciones** | Entregar confirmación de pago por el canal existente (consumidor de eventos) | ✅ reusa lo de Suscripciones |

## 3. Ledger financiero mínimo (capacidad de Cobranza)
- **Registra movimientos:** cargos, pagos, bonificaciones, intereses, ajustes, cancelaciones.
- **El Estado de Cuenta se construye consultando el Ledger**, no con lógica distribuida en SPA/gateway.
- **Fuente de verdad financiera = el sistema contable activo de la organización** (vía **adaptador**).
  En esta implementación inicial dicha fuente es **Odoo**. **El Ledger no duplica esa verdad; centraliza
  la consulta y el cálculo del Estado de Cuenta.** *(Sin base financiera paralela; el contable es
  reemplazable por adaptador, fiel a la filosofía de la plataforma.)*
- Contrato mínimo: `registrarMovimiento(...)` · `estadoDeCuenta(cliente/servicio)` (saldo, vencido, por vencer).

## 4. Motor de Pago (depende de `PaymentAdapter`, nunca de Stripe)
- El Motor de Pago **solo conoce la interfaz `PaymentAdapter`** (autorizar intención → resultado;
  confirmar vía webhook). **Stripe es únicamente el primer adaptador**; el Motor jamás lo referencia
  directamente. Cambiar/añadir proveedor = otro adaptador, sin tocar el Motor ni la vertical.
- Implementa la costura **`startPayment()`** ya dejada en Sprint 1.
- **Idempotencia** (cobro no se aplica dos veces) + **conciliación** (anti doble pago online+OXXO/banco)
  + manejo explícito de **en proceso / rechazado**. Comisiones absorbidas por Sentinela (PROD_01).

## 5. Flujo de confirmación (todo desacoplado por eventos)
```
pago.confirmado (Pagos, vía webhook)
   → Ledger registra el pago
   → factura(s) liquidada(s)  → evento factura.pagada
        → CFDI service (async, REINTETABLE)        ← si el PAC falla, el PAGO SIGUE VÁLIDO
        → Reactivation Policy (evalúa, §6)          ← reactiva solo si se cumplen las condiciones
        → Notificaciones (confirmación al cliente)
```
**El CFDI NO es parte de la transacción del pago.** Un fallo del PAC no invalida el pago; el CFDI se
reintenta. **La reactivación NO ocurre directo al confirmar el pago**, sino tras `factura.pagada` y solo
si la **Policy** lo permite.

## 6. Policy de Reactivación (no es consecuencia directa del pago)
Existe una **Policy** explícita evaluada ante `factura.pagada`. Condiciones MÍNIMAS (todas):
1. **Factura totalmente pagada.**
2. **Servicio suspendido por cobranza.**
3. **No existen otras facturas vencidas** del servicio.
→ Solo entonces se reactiva el servicio y se emite `servicio.reactivado`. (Evaluación **por servicio**.)

## 7. Event Store mínimo (capacidad reutilizable, mínima)
Nace como capacidad reutilizable pero **mínima**. Expone **solo**:
- `append(evento)`
- `read(filtro)`
- `byAggregate(id)`

**NO** se construye todavía: CQRS · Replay · Projections · Event Sourcing · Timeline. Catálogo mínimo
de eventos: `pago.iniciado` · `pago.confirmado` · `pago.rechazado` · `factura.pagada` ·
`servicio.reactivado` (+ reusa de Suscripciones: `factura.creada` · `factura.por_vencer` ·
`servicio.suspendido`). Consumidores en este sprint: **Notificaciones** y los servicios internos
(CFDI, Reactivation Policy). *(Sin Timeline: ningún consumidor de UI de eventos aún.)*

## 8. Indicadores MVP (sin Dashboard Engine)
Solo **3 consultas básicas** sobre el Ledger: **cobrado hoy · cartera vencida · pagos pendientes**.
Nada de motor de dashboards ni analítica adelantada.

## 9. Flujos (MVP de PROD_01)
**Usuario:** ve saldo/facturas (desde el **Ledger**) → selecciona → resumen → paga (tarjeta) →
**confirmación** → saldo actualizado; el recibo/CFDI llega (puede tardar/reintentarse); el/los
servicio(s) se reactiva(n) si la Policy lo permite. Variantes: en proceso / rechazado (reintentar).
**Interno:** §5. Cobranza **supervisa excepciones** (no concilia estos pagos).

## 10. Cómo encaja con el Sprint 1 (reusa, no reinventa)
- **Reusa:** facturas/cuenta (`sentinela_api`), UX selección+resumen+`startPayment` (seam ya hecha),
  timbrado CFDI, Design System, Gateway.
- **Construye:** Ledger mínimo + `PaymentAdapter`+adaptador Stripe + `startPayment()` real +
  Event Store mínimo (append/read/byAggregate) + Reactivation Policy + CFDI como consumidor async +
  notificación por evento + 3 indicadores.

## 11. Cómo esta vertical hace crecer las capacidades (orgánico)
- **Ledger, Pagos, Event Store, Notificaciones** nacen **mínimos**, exigidos por Cobranza.
- **Ninguno** se generaliza "por si acaso": Seguridad (Sprint 3), Soporte (Sprint 4) e IA
  **tensionarán** estos contratos y los harán madurar — y solo entonces se promoverán (regla de oro).
- **Timeline** no existe hasta que una 2ª vertical necesite consumir eventos en UI.

## 12. Criterios de aceptación (verificable)
- Pago de 1+ facturas → `pago.confirmado` → Ledger registra → `factura.pagada` → CFDI emitido (o
  **pendiente reintetable** si el PAC falla, con el pago **válido**) → Policy reactiva **solo** si se
  cumplen sus 3 condiciones → notificación recibida → Estado de Cuenta actualizado **desde el Ledger**.
- Pago rechazado → mensaje claro + reintento; sin registrar pago ni reactivar.
- **Idempotencia:** webhook/reintento duplicado no doble-aplica.
- **Conciliación:** pago online no se duplica con depósito OXXO/banco.
- **Motor de Pago** no referencia Stripe directamente (solo `PaymentAdapter`).
- **Estado de Cuenta** proviene del **Ledger** (no de lógica dispersa).
- Reactivación **por servicio**, gobernada por la **Policy**.

## 13. Riesgos
Doble pago (online+depósito) · "en proceso" vs "confirmado" · idempotencia del webhook · fallo del PAC
(mitigado: CFDI desacoplado/reintetable) · reactivación indebida (mitigada por la Policy) · acoplar el
Motor a Stripe (mitigado por `PaymentAdapter`) · duplicar contabilidad (mitigado: Ledger sobre la verdad existente).

## 14. Orden de construcción
1. **Event Store mínimo** (`append/read/byAggregate`).
2. **Ledger mínimo** (sobre la contabilidad existente) + Estado de Cuenta.
3. **Motor de Pago** (`PaymentAdapter` + adaptador Stripe) + `startPayment()` + webhook→`pago.confirmado`.
4. **factura.pagada** → **CFDI async** + **Reactivation Policy** + **Notificaciones**.
5. **Indicadores** (3 consultas) + pruebas de aceptación §12.

## 15. Verificación de filosofía (regla de oro)
Repaso del documento: **ninguna capacidad se construye para reutilizarse**; todas nacen **mínimas**
exigidas por Cobranza. **Sin** Timeline, Dashboard Engine, CQRS/Replay/Projections, medios guardados,
ni abstracciones adelantadas. El Event Store es reutilizable pero **mínimo** (3 operaciones). La
reutilización llegará **cuando una 2ª vertical la demuestre**.

---
**Estado:** especificación lista para construir. **No se inicia construcción hasta cerrar la UAT del
Sprint 1** (STAGING congelado; gate solo con "La UAT terminó"). Sprints siguientes (Seguridad, Soporte,
Catálogo, SentiBot) seguirán el mismo patrón vertical y harán madurar estas capacidades.
