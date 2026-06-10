---
name: alta-suscripcion
description: >-
  Da de alta una suscripción nueva en sentinela_subscriptions (cliente WISP/internet,
  GPS, o alarma/monitoreo): crea/usa el partner con sus datos fiscales, crea la sub
  con su plan, deriva los servicios del plan, y deja fechas/ciclo correctos. Úsalo
  cuando Enrique diga "da de alta a este cliente", "crea la suscripción de...",
  "alta nueva". Conoce las trampas del constraint de servicios y del modelo de cobro.
---

# Alta de suscripción

El módulo `sentinela_subscriptions` es el corazón operativo (reemplaza MASadmin/Argus).
Una sub liga un partner + un plan (producto) + servicios derivados + fechas de cobro.

## 1. Partner (cliente)
- Reusar el `res.partner` si ya existe; si no, crearlo.
- **Datos fiscales** (pestaña Facturación/CFDI): RFC, régimen, uso CFDI, y la
  `fiscal_position_id` correcta — **8% frontera** vs **16% interior** (define el IVA
  de la factura). Domicilio del servicio con **Colonia** (`street2`) para el contrato.
- `invoice_grouping_method`: `individual` (default, 99% de los casos), `by_branch`
  (agrupa por sucursal/`service_address_id`) o `global`. Solo cambiar si el cliente
  factura agrupado.
- `auto_send_mail` si quiere recibir la factura por correo; `auto_invoice` (campo
  "Generar Factura (No Remisión)") si lleva CFDI timbrado.

## 2. Suscripción
- Seleccionar el **plan** (`product_id`). Al hacerlo, el `_onchange_product_id`
  **prellena los servicios** (`service_inclusion_ids`) desde la matriz
  `sentinela.product.service.inclusion` → revisarlos antes de guardar y ajustar
  `extra_price` si aplica.
- ⚠️ **Trampa del constraint:** `_check_service_inclusions_complete` exige que el plan
  tenga TODOS sus servicios. Desde v18.0.1.3.53 `create()` los pre-deriva (cubre form,
  XML-RPC y scripts), pero si sale "el plan X no tiene definido todos los servicios",
  es que la matriz de inclusiones del plan está incompleta — completar la matriz, no
  forzar el alta. (`product_id` es `product.template`; NO usar `.product_tmpl_id`
  sobre él — ese fue el bug que bloqueaba TODA alta, v.29.)
- **Modelo de cobro** (ver memoria `reference_subscriptions_billing_model`):
  - Internet/GPS = tarifa mensual, `qty` = meses del ciclo.
  - Alarma = precio del periodo (productos -3/-6/-12), `qty=1`.
  - "Ciclo de Facturación" = ciclo permanente. Adelanto único = botón "Cobro Adelantado".

## 3. Fechas y estado
- `state` = `active` para que entre al ciclo.
- `start_date` y `next_billing_date` según arranque. (Baseline del arranque: subs en
  `start_date=2026-06-01`, `next_billing_date=2026-07-01`; primer ciclo de
  pre-facturas el 26-jun.) El cron de facturación genera la factura cuando
  `next_billing_date <= hoy` y avanza la fecha sola.

## 4. Provisioning según tipo
- **WISP/internet:** la sub provisiona el secret PPPoE en CCRsentinela (perfil con
  pool). Verificar que navegue. NO confundir con FFW/internet-static (va sobre el
  Balanceador con NAT 1:1 + queue, no PPPoE).
- **GPS:** plataforma (SentiCar/Tracksolid/Smake), `sim_iccid` floLIVE si aplica,
  modo (vehículo/móvil) según el plan.
- **Alarma/monitoreo:** liga al módulo `sentinela_monitoring`.

## 5. Verificar y reportar
- Confirmar: sub creada con número SUB-xxxx, servicios derivados, fiscal_position
  correcta, fechas, y provisioning aplicado.
- Si es WISP, confirmar navegación real; si GPS, confirmar SIM/plataforma.

## Acceso
```bash
ssh -p 2222 -i ~/.ssh/id_rsa_sentinela egarza@192.168.3.2 \
  'docker exec -i odoo18-migration-web-1 odoo shell -d Sentinela_V18 --no-http' < script.py
# env.cr.commit() para persistir; respaldar antes de altas masivas
```
Para altas masivas, respaldar el estado previo a un `.backup_*.json` como referencia.
