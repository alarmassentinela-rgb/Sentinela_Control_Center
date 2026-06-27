# Resumen de sesión — 27 de junio de 2026

Continuación del 26-jun. Foco de hoy: **datos del contacto (teléfonos)**, **Forma de Pago en el PDF**, **facturación GLOBAL consolidada (formato oficial)** y **alta de GPS a una suscripción**. (Hubo también commits `feat(coc)`/`feat(web)`/`feat(gateway)` del Portal COC Sprint 1 — otra línea de trabajo, no cubierta aquí.)

**Versiones finales:** `sentinela_subscriptions 18.0.1.4.26` · `sentinela_cfdi_prodigia 18.0.1.3.15` · `sentinela_monitoring 18.0.1.32.1` · `sentinela_syscom 18.0.1.8.7`

---

## 1. Contacto: teléfono fijo + extensión + celular (res.partner)
- **Extensión** del teléfono (`phone_extension`, máx 4 díg) en un **solo renglón** con el teléfono (`o_row`, reemplazando el campo phone para no descuadrar el grupo).
- **Celular sin widget phone** (quita el "llamar/SMS" al pasar el cursor).
- Botones **"LLAMAR UCM"** (de sentinela_monitoring, en tel y celular) → ahora **ícono** (no ocupan medio renglón). `monitoring 18.0.1.32.1`.
- **Teléfonos adicionales (lista) RETIRADO de la UI:** se intentó (pestaña → inline → form emergente) pero **no dejaba agregar** en el navegador del usuario (ni en incógnito). Causas detectadas y corregidas en el camino: el campo `name` recibía auto el widget `field_partner_autocomplete` (rompía "Agregar línea"); el `ext` suelto descuadraba el grupo. Aun así el cliente pidió **dejar solo fijo+celular por ahora**. El modelo `res.partner.phone` y el campo `phone_line_ids` **quedan dormidos en el código** (sin UI) para retomar — **falta el error de consola (F12)** para diagnosticar el bloqueo final. `subscriptions 18.0.1.4.11 → .4.18`.

## 2. Forma de Pago en el PDF (cfdi 18.0.1.3.15)
- El PDF mostraba **"99 – Por definir"** para clientes PUE porque leía el campo de la factura (`l10n_mx_edi_payment_method_id_code`, default 99) que nadie llena. El **XML/timbre sí salía bien** (lo deriva del cliente).
- **Fix:** el PDF ahora deriva la Forma de Pago **igual que el XML**: PPD → "99 Por definir"; PUE → forma del cliente (`invoice_payment_form`, ej. **"03 – Transferencia"**). Aplica a TODAS las facturas (PDF ahora coincide con el timbre).

## 3. Facturación GLOBAL consolidada — FORMATO OFICIAL (subscriptions 18.0.1.4.19 → .4.22)
`_billing_generate_invoice`: cuando el cliente es `invoice_grouping_method='global'`:
- **Consolida por (producto, precio, periodo):** UNA línea por grupo, **cantidad = nº de servicios/sucursales** (antes: una línea por sub).
- **Periodo UNA sola vez** como renglón de **nota** al final ("Periodo facturado: …"), no repetido por línea. Si hubiera periodos distintos en la misma factura, se deja por línea (salvaguarda).
- **Toggle por cliente `invoice_show_branches`** ("Detallar sucursales en factura", en pestaña Facturación/CFDI, visible solo si es global):
  - **Sí** → "Servicio: \<producto\> | Sucursales: nombre1, nombre2, …"
  - **No** → solo "Servicio: \<producto\>" (la cantidad va en su columna).
- Se quitó el "(N servicios)" redundante (la columna Cantidad ya lo indica).
- **Intacto:** postear, avance de ciclo (`next_billing`), candado anti-duplicado (el periodo va en la nota → lo sigue encontrando), CC y correo. Individual/by_branch sin cambios.
- **Verificado en PROD** con el método oficial vía `rollback` (no persiste): COPIZZA (1 línea, qty 9, $14,850.02) y Control de Plagas (mixto: 3 líneas). Vistas previa enviadas a egarza@.

## 4. GPS agregados a SUB-0398 (Control Internacional de Plagas)
- Del archivo **`Descargas/ciplagas gps.xlsx`** (plataforma **Smake**): **6 equipos** creados en SUB-0398 (id 1208) con nombre, IMEI e ICCID (equipo=N01): Ram Rapid 821-A, Ram Rapid 19A, FORD LOBO, Ram Rapid 29B, SONIC, f-150.
- Solo **registro en Odoo** (Smake no tiene API de provisioning como SentiCar). El ICCID se tomó del campo SIM (19 díg); el archivo traía sufijo "f" (artefacto de exportación Smake).
- ⚠️ El sub de GPS factura **por nº de equipos** → la factura de Control de Plagas pasó de 1 a **6 equipos** en la línea GPS (total previa $2,100 → $3,849.97).

## 5. Panel de automatización de crones (Ajustes) — NUEVO
**Suscripciones (subscriptions .4.19→.4.26):** bloque **"⚙️ Automatización de Facturación y Cobranza"** en `res.config.settings`:
- **Capa 1:** toggles independientes ON/OFF (ir.cron.active) de 5 crones: generar pre-facturas, **timbrar (Prodigia)** (mueve también `auto_stamp_enabled`), auto-suspender, recordatorios, fin de leasing + **estado en vivo** (🟢/🔴, intervalo, última/próxima en hora local).
- **Capa 2:** **control MASTER** (onchange enciende/apaga todos), **Hora** (float_time, recalcula `nextcall` a la próxima ocurrencia en la tz del usuario vía `_bc_tz`, fallback America/Mexico_City) e **intervalo** (número/unidad) por cron. El timbrado también tiene Hora.
- get_values/set_values sobre los `ir.cron` (referencia por xmlid).

**Syscom (syscom .8.7):** mismo control en **Ajustes → Syscom** (bloque "Sincronización de Catálogo"), self-contained: ON/OFF + Hora + Cada + estado del cron `ir_cron_syscom_sync`.

**Fix bloqueante syscom (.8.6):** `sync_brands`/`sync_categories` eran **Text con config_parameter** → `res.config.settings` no admite Text → **rompía abrir TODA la página de Ajustes** (default_get). Cambiados a **Char con `widget="text"`** (conserva multi-línea; la lista de marcas se preservó intacta). Ajustes ya abre.

## Crones — configuración aplicada (PROD)
- **Generar Pre-Facturas:** 1:00 am, diario (ON).
- **Auto-Timbrar:** **anclado 1:30 am, cada hora** (ON). Toma las "pending" tras el lote de la 1:00. Flujo: 1:00 remisiones por correo → 1:30 facturas timbradas por correo → cada hora las manuales del día. **Un cliente de factura NUNCA recibe remisión** (el generar solo envía remisiones; las facturas se mandan tras timbrar; el código lo garantiza: `not partner.requiere_factura` al generar).
- **Syscom (Update Prices and Stock):** estaba **OFF desde 24-jun**; **reactivado a las 3:00 am, diario**.

## Manual PDF enviado a Telegram
Manual "Automatización de Facturación y Cobranza (crones)" (HTML→wkhtmltopdf del contenedor, 3 págs, pantallas mock fieles) → Telegram de Enrique (bot SentinelaNet, chat 7965190381).

## Técnica reutilizable: vista previa de factura SIN afectar la cuenta
Patrón usado varias veces hoy: armar la factura (borrador, o el método oficial `_billing_generate_invoice`), **renderizar el PDF**, **enviarlo a egarza@** por `ir.mail_server`, y **`unlink`/`rollback`** → cero efecto contable (borrador no consume folio; el rollback deshace todo; en Odoo 18 el folio se deriva, sin huecos). Sin timbrar → el PDF dice "REMISIÓN".

---

## Pendientes para la próxima sesión
1. **Teléfonos múltiples por contacto** (dormido): si se retoma, conseguir el **error de consola** al "Agregar línea" para cerrar por qué la lista editable no funcionaba en el navegador del usuario. Modelo `res.partner.phone` ya existe.
2. **Go-live facturación:** ⚠️ corrección — los crones de facturación **YA ESTÁN ON** y corriendo (el freeze se levantó antes del 27-jun). Generar 1:00 / Timbrar 1:30 c/hora / Syscom 3:00. Ya configurables desde el panel de Ajustes. La memoria del freeze quedó obsoleta.
3. **Pasarela de pago:** el botón "pago en línea" del correo lleva al portal pero no hay gateway activo (Mercado Pago/Stripe/Conekta).
4. **QR Telegram inline en Gmail:** sin validar visualmente en cliente real.
5. **GPS Smake:** los 6 equipos quedaron solo en Odoo; si se migran a SentiCar más adelante, hay que provisionar en Traccar (ver [[project_kawac_migracion_senticar]]).

## Verificaciones reales hechas
- Forma de Pago: render confirmó "03 – Transferencia" (PUE) y ya no "Por definir".
- Global consolidada: método oficial en PROD (rollback) → líneas/cantidades/total correctos (COPIZZA $14,850.02; Control de Plagas $3,849.97 con 6 GPS); 0 facturas creadas (cuentas intactas).
- Toggle sucursales: Control de Plagas con `invoice_show_branches=False` → líneas sin nombres ni "(N servicios)".
- GPS: SUB-0398 quedó con 6 equipos (verificado).
- **Sin validar:** QR Telegram inline en Gmail; botón pago en línea (sin pasarela).
