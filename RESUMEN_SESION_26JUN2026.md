# Resumen de sesión — 26 de junio de 2026

Sesión enfocada en **facturación CFDI**: por qué no se timbró la factura de Rocío Calderón, función de **cancelación ante el SAT**, rediseño del **formato de factura/remisión**, y **correo branded** de facturas/remisiones. (Ese día hubo también commits del Portal COC — WS-2 aislamiento/record rules y runbook deploy — que son otra línea de trabajo, no cubierta aquí.)

**Versiones finales:** `sentinela_cfdi_prodigia 18.0.1.3.8` · `sentinela_subscriptions 18.0.1.4.10`

---

## 1. Por qué no se timbró INV/2026/00171 (Rocío, SUB-0262) — CAUSA RAÍZ
El cron **"CFDI: Auto-Timbrar" (id 67)** estaba activo y bien configurado (`auto_stamp_enabled=1`, `test_mode=False`), pero **reventaba cada hora**:
```
AttributeError: 'account.move' object has no attribute '_cron_auto_stamp_prodigia'
```
El método existía en disco (rsync 25-jun 11:06) y la DB ya tenía la versión 18.0.1.2.3, **pero el contenedor `odoo18-migration-web-1` arrancó el 24-jun 12:50** — un día ANTES del archivo nuevo → los workers vivos corrían el Python viejo, sin el método. La factura quedó en `pending` sin que nadie lo notara.
- **Fix:** `docker restart odoo18-migration-web-1` → el cron timbró bien.
- **Lección (en memoria):** TODO `-u` en prod va **seguido de `docker restart`**. El `-u --stop-after-init` actualiza DB/registro, NUNCA el proceso vivo. Aplica a campos, métodos, **crones** y **reportes QWeb**.

## 2. Leyenda "DOCUMENTO DE PRUEBA" hardcodeada (v18.0.1.2.4)
Estaba fija en `report_invoice.xml` → salía en TODA factura timbrada. Condicionada a `is_test` (config param `test_mode`). El timbre real se verifica por el XML (CSD del emisor real vs CSD genérico SAT `30001000000400002434`), no por el watermark.

## 3. Cancelación de CFDI ante el SAT (NUEVO) — v18.0.1.3.0 → .3.2
- Botón **"Cancelar ante el SAT"** + wizard `sentinela.cfdi.cancel.wizard` (motivo 01-04 + folio sustitución si 01).
- Método `action_cfdi_cancel_prodigia`. **Endpoint correcto descubierto sondeando con UUID falso** (seguro):
  - `https://timbrado.pade.mx/servicio/rest/cancelacion/cancelar` · **POST** (GET da 405) · query params.
  - `arregloUUID = 'UUID|motivo|folioSustitucion'` (3 campos) + **`opciones=CERT_DEFAULT`** (sin CERT_DEFAULT pide "contraseña del archivo").
  - Respuesta XML `<servicioCancel>`: `statusOk` + `<cancelacion><codigo>` por UUID (**201** aceptada / 202 ya cancelada / 205 no existe) + `acuseCancelBase64`.
  - Éxito → `cfdi_status='cancel'` + guarda acuse + fecha + motivo.
- **Candado anti-doble-timbrado:** `action_cfdi_stamp_prodigia` lanza UserError si ya hay UUID válido.
- ⚠️ `integracion/cancelarCfdiConOpciones` NO funcionó (no reconoce el arreglo de folios); se usa `cancelacion/cancelar`.

## 4. Cancelación real de la factura de Rocío
UUID **12458E1C-A42B-4224-9C17-31CEB7FC3916**, motivo 02 → `statusOk=True`, estatus 201 "Solicitud de cancelación recibida", `cancelados=1`, acuse guardado. **Cancelada ante el SAT.**

## 5. Ajustes al formato factura/remisión (`report_invoice.xml`)
- **Email emisor** del PDF → `cobranza@sentinela.com.mx` (texto informativo).
- **Régimen fiscal receptor** con descripción (`t-field` → "612 - Personas Físicas...").
- **Uso de CFDI** con descripción (`t-field` → "G03 - Gastos en general").
- **Condiciones de Pago** ahora desde `invoice_payment_condition` del cliente (pestaña Facturación/CFDI): Contado/**Crédito**/Otro — NO desde el plazo de pago de Ventas. (Rocío = Crédito.)
- **Método de Pago** real (PUE/PPD) + descripción (antes hardcodeaba "PUE"; el XML real ya iba PPD).
- **Datos bancarios** según tipo de cliente: **Banorte** (cuenta `0668059925` / CLABE `072818006680599252`) si requiere factura, **HSBC** (`6487156501` / CLABE `021818064871565017`) si es remisión. Helper `_get_emisor_bank_info()`.
- **Concepto por MES**: "CORRESPONDIENTE AL MES DE \<MES\> \<AÑO\>" (rango si ciclo multi-mes) en vez de "Periodo: fecha al fecha". Helper `_billing_period_label()` (subscriptions), usado también por el candado anti-duplicado.
- **Notas** desde la sub (ver §6), en **banda de ancho completo** debajo de conceptos y arriba del "Importe con letra".

## 6. Campo "Notas para Factura" en la suscripción (NUEVO)
`invoice_notes` (Text) en `sentinela.subscription`, separado de "Notas Internas". Lo lee el PDF (`o.subscription_id.invoice_notes`, robusto para facturas agrupadas). Sirve para "Orden de compra XXXX" o indicaciones del cliente; sale en TODAS las facturas de esa sub. Capturado en SUB → pestaña Notas.

## 7. Nueva factura de Rocío (id 404)
Servicio corregido en la sub: producto **1966 "PLAN INTERNET 20MB/7MB" $509.26** (antes 1975 $601.85, por eso el total estaba mal). Generada en borrador para revisión, luego confirmada y **timbrada**: **INV/2026/00171**, UUID **A28780A9-AF20-4A6A-B25B-948CA68B2D11**, total **$550.00** (IVA 8% frontera), método PPD, mes de junio.
- ⚠️ **Reuso de folio 00171:** la factura vieja (id 401, con el CFDI cancelado 12458E1C) estaba en borrador y **se eliminó** → liberó el folio y la 404 lo tomó. Ante el SAT coexisten el folio 00171 cancelado (12458E1C) y el válido (A28780A9) — legal (SAT identifica por UUID). Al borrar la 401 **se perdió de Odoo el acuse de cancelación** (sigue cancelada en SAT; descargable de Prodigia).

## 8. Correo de facturas/remisiones
- **Remitentes:** facturas/remisiones = **facturacion@**; recordatorios de cobranza (overdue_soft, pre_suspend, suspended) = **cobranza@** (ya estaban en el código del módulo). Plantilla factura = `account.email_template_edi_invoice` (id 7), `email_from` en DB.
- **Correo branded** (cuerpo de la plantilla id 7, vive en DB): logo, botón **"Ver y Pagar en Línea"** (portal), **datos bancarios** por tipo, **pago en tienda** (7-Eleven factura / OXXO+tarjeta HSBC remisión), **WhatsApp 868 125 4500** (wa.me clickeable) para compartir comprobante, e **invitación a Telegram** (botón + **QR inline vía cid**, para que se vea en Gmail). Sin la referencia interna (invoice_origin) que confundía.
- `_cfdi_send_invoice_email` **reescrito**: envía por `ir.mail_server` con QR inline (cid), PDF + XML, CC (cliente+sub) y BCC opcional. **Remisiones unificadas** a este mismo método (antes iban más simples y sin PDF).
- **Pruebas:** factura de Rocío enviada a rociodecristal@gmail.com con **CCO egarza@** (primer test); luego pruebas solo a egarza@ con el cuerpo branded + QR.

## 9. Estado del correo / freeze (sin cambios de fondo)
- **SMTP de salida activo** (`mail.sentinela.com.mx:465`) y **cron de cola activo** → el correo nuevo se envía.
- Los **163 mail.mail en estado `cancel`** (ene–jun) NO se envían (la cola solo procesa `outgoing`; hay 0 outgoing). Quedan muertos a propósito del freeze.
- **Crones de facturación siguen OFF** (freeze hasta go-live ≈1-jul): id 39 Pre-Facturas, id 55 Auto-Suspender, id 56 Recordatorios.
- **Pasarelas de pago: TODAS deshabilitadas** → el botón "pago en línea" lleva al portal (ver/descargar); el pago real aparecerá cuando se active una pasarela.

---

## Pendientes para la próxima sesión
1. **Botón "Ver y Pagar en Línea":** no hay pasarela de pago activa. Decidir: activar una (Mercado Pago / Stripe / Conekta, con credenciales) **o** relabelar a "Ver factura en línea" mientras tanto.
2. **Verificar el QR de Telegram inline en Gmail** (cliente real). Si saliera como adjunto en vez de inline, pasar el correo a estructura `multipart/related`.
3. **Folio 00171 reusado / acuse perdido:** si se necesita el acuse de cancelación de 12458E1C, descargarlo del portal Prodigia. Evaluar política para no borrar facturas con CFDI (aunque sea cancelado).
4. **Go-live facturación (≈1-jul):** reactivar crones id 39/55/56 (ver [[project_email_freeze_migracion]]).
5. **Limpieza opcional** de los 163 mail.mail en `cancel`.
6. **Warning menor:** `sentinela_subscriptions/__manifest__.py` sin clave `license` (Odoo asume LGPL-3).

## Verificaciones reales hechas
- Cancelación de Rocío: confirmada por respuesta del SAT (statusOk/201/cancelados=1).
- Timbre 404: XML con Total 550.00, MetodoPago PPD, descripción por mes.
- Formato: render HTML confirmó cobranza@/régimen/uso/condiciones(Crédito)/banco(Banorte vs HSBC)/notas en banda/sin referencia.
- Correo: envíos por `ir.mail_server` con message-id devuelto; QR disponible en el método real.
- **Sin validar:** render inline del QR específicamente en Gmail (cliente real).
