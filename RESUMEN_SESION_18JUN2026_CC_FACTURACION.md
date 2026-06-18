# Resumen de sesión — 18 de junio de 2026 (parte 2: CC en facturación)

Sesión enfocada en **un solo tema**: poder enviar la factura/remisión recurrente a
**varios correos** (no solo al del cliente). Módulo `sentinela_subscriptions`.

## Punto de partida (cómo estaba)
- La factura/remisión del ciclo se enviaba **solo a `partner_id.email`** (el correo de la
  ficha del cliente), si la suscripción tenía `auto_send_mail=True`. Sin opción de más
  destinatarios. Lógica en `subscription.py::_billing_generate_invoice` (~línea 976).
- No existe campo de "correo de facturación" aparte; `senticar_user_email` es solo para la
  plataforma GPS, no se usa para correos de factura.

## Lo que se hizo

### 1. CC a nivel SUSCRIPCIÓN — v18.0.1.4.0 (commit `c167b4c`, tag `v18.0.1.4.0-sentinela_subscriptions`)
- Campo nuevo `extra_invoice_partner_ids` (Many2many a `res.partner`) en la suscripción:
  contactos del cliente que reciben **COPIA (CC)** del documento del ciclo, además del
  correo principal.
- Vista: en "Preferencias de Facturación", **visible solo cuando `auto_send_mail` está
  activo**. Dominio `[('id','child_of',partner_id),('id','!=',partner_id)]` → solo lista
  contactos del propio cliente.
- Envío: en `_billing_generate_invoice`, se arma `email_cc` con los correos de los contactos
  seleccionados (excluye al principal y a los sin correo) y se pasa a
  `template.send_mail(..., email_values={'email_cc': ...})`.

### 2. CC a nivel CLIENTE — v18.0.1.4.1 (commit `f90091f`, tag `v18.0.1.4.1-sentinela_subscriptions`)
- **Motivo:** para clientes con **factura global** (ej. 9 sucursales = 9 subs → 1 sola
  factura), poner el CC en cada suscripción es incoherente. La preferencia de agrupación
  vive en el cliente, así que el CC también debe poder configurarse ahí, **una sola vez**.
- Campo nuevo `invoice_cc_partner_ids` (Many2many a `res.partner`) en **`res.partner`**:
  contactos que reciben CC de **TODAS** las facturas/remisiones del cliente, sin importar
  la agrupación.
- Vista: ficha del cliente → "Condiciones de Pago y Facturación" → "Comprobante Fiscal".
  Dominio = contactos del cliente.
- Envío: ahora `cc_partners = (subs_list.mapped('extra_invoice_partner_ids') |
  partner.invoice_cc_partner_ids).filtered(...)` → **unión deduplicada** de CC de cliente
  + CC de suscripción.
- Matriz de uso resultante:
  | Caso | Dónde se configura el CC |
  |---|---|
  | 1 factura global por N sucursales | **Solo en la ficha del cliente** |
  | 1 factura por sucursal (by_branch) | En el cliente |
  | Individual con correo distinto por contrato | En la suscripción |

## Verificación (REAL, en STAGING `:8075`, sin enviar nada)
Ambas features se probaron ejecutando el **flujo real** `_billing_generate_invoice` dentro
de un `odoo shell` en una transacción **sin commit → rollback** (limpieza automática, cero
correos, cero rastro). El SMTP de STAGING además está **inactivo** (`ir_mail_server.active=f`),
doble seguro contra envío real.
- **Feature 1:** SUB-0142 → `mail.mail` con `email_cc` = los 2 contactos seleccionados;
  Para = correo principal del cliente. ✅
- **Feature 2 (global):** cliente con 2 subs activas en modo `global` → **UNA sola factura**
  (2 líneas); `email_cc` tomado **solo de la ficha del cliente** (3 contactos), subs sin CV
  propio. ✅
- Post-prueba verificado por SQL: 0 contactos de prueba, 0 filas de CC, grouping del cliente
  restaurado a su valor original. STAGING limpio.

## Despliegue
- Flujo completo por feature: rsync local→server → `-u Sentinela_STAGING` (odoo-lab) →
  prueba → release (commit+tag+push) → `-u Sentinela_V18` → **restart `odoo18-migration-web-1`**
  (campos Python nuevos) → verificación.
- **PRODUCCIÓN (V18) quedó en `18.0.1.4.1`.** Verificado: HTTP 200, campos
  `extra_invoice_partner_ids` (res.subscription) e `invoice_cc_partner_ids` (res.partner)
  registrados, tablas relación `sentinela_sub_extra_invoice_partner_rel` y
  `res_partner_invoice_cc_rel` creadas.

## Pendientes / notas
1. **Freeze de facturación SIGUE activo** (crones de pre-facturas OFF hasta go-live ~1-jul).
   Los correos NO empezarán a salir solos hasta reactivar. Se pueden **capturar los CC** en
   las fichas/subs desde ya, sin riesgo.
2. Para que un contacto reciba CC debe estar como **contacto hijo del cliente CON correo**.
   Si no existe, primero darlo de alta en la ficha del cliente.
3. **Sin validar en navegador real** el render del campo en el form (solo `-u` + SQL); la
   prueba de envío sí fue end-to-end por shell. Si al abrir el form hubiera algún detalle de
   render, revisar con F12 / STAGING.
