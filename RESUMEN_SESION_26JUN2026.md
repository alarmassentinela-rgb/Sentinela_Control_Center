# Resumen de sesión — 26 de junio de 2026

Sesión enfocada en **facturación CFDI**: por qué no se timbró la factura de Rocío Calderón, función de **cancelación ante el SAT**, rediseño del **formato de factura/remisión**, y **correo branded** de facturas/remisiones. (Ese día hubo también commits del Portal COC — WS-2 aislamiento/record rules y runbook deploy — que son otra línea de trabajo, no cubierta aquí.)

**Versiones finales:** `sentinela_cfdi_prodigia 18.0.1.3.14` · `sentinela_subscriptions 18.0.1.4.10` · `sentinela_syscom 18.0.1.8.5`

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

## Continuación de la sesión (cambios posteriores al primer corte)

### A. Envío de factura/remisión por correo (cfdi 18.0.1.3.9 → .3.14)
- **Timbrar = timbrar + enviar:** `action_cfdi_stamp_prodigia` ahora, tras timbrar OK, manda el correo branded al cliente (manual y lote). Se quitó el envío duplicado del cron. Context `skip_cfdi_email=True` para omitir.
- **Botón "Timbrar" ya muestra el error del PAC** (antes lo atrapaba en silencio → "no hacía nada"): si queda en `error`, devuelve una notificación roja con el `cfdi_message`.
- **Botón propio "Enviar al cliente"** (correo branded) + **se OCULTÓ el "Enviar e imprimir" nativo de Odoo** (`action_invoice_sent`, 2 variantes → `invisible=1`). El nativo envolvía en su layout, metía su propio "Ver Factura" al portal y NO traía el QR.
- **Botón "Ver Factura (PDF)"** en el correo → abre/descarga el PDF directo (portal `report_type=pdf` + token); además del "Ver y Pagar en Línea".
- **Wizard de envío** (`sentinela.cfdi.send.wizard`): "Enviar al cliente" abre ventana para ELEGIR a qué correos enviar (contactos del cliente precargados, con nombre+correo) y/o capturar **correos manuales**. `_cfdi_send_invoice_email` acepta `force_recipients`/`force_to`/`extra_bcc`.
- `_cfdi_send_invoice_email` reescrito: envía por `ir.mail_server` con **QR Telegram inline (cid)** (Gmail bloquea base64), PDF+XML, CC/BCC. Remisiones unificadas a este método.

### B. INV/2026/00169 no timbraba + Clave SAT en el cron de Syscom (syscom 18.0.1.8.2)
- **Causa:** la batería LK5.512 no tenía Clave SAT (`l10n_mx_edi_code_sat`) → el XML salía con `01010101` → el SAT rechaza el 8% frontera (`[CFDI40999]`). El "no hacía nada" del botón era el error silencioso (ya corregido, ver A).
- **Hueco encontrado:** el cron de Syscom solo guardaba `syscom_sat_description`/`syscom_sat_unit_key` (informativos); **NO** llenaba `l10n_mx_edi_code_sat` (solo el wizard de import lo hacía). La API SÍ trae `sat_key` (ej. 26111701) en listado y detalle.
- **Fix:** el cron ahora llena `l10n_mx_edi_code_sat`/`l10n_mx_edi_um_code_sat` desde `sat_key`/`clave_unidad_sat` en Fase 1 y Fase 2, **solo si están vacías**. ~9,752 productos vendibles sin clave se irán llenando en las nocturnas.
- **00169 timbrada:** clave 26111701 al producto, UUID **B39769F4-54DA-494F-9BA6-9A61F0F8ABA3**.

### C. Bobinas de cable: vender por metro Y por bobina (syscom 18.0.1.8.3, migración de datos)
- Modelo del cliente: **compra solo por bobina; vende por metro y también bobina completa.**
- Solución UdM: cada bobina con **UdM venta = Metro** y **UdM compra = Bobina{N}** (misma categoría Length → en la línea de venta eliges "m" o "Bobina{N}"). UdM creadas: Bobina100/152/305/500/1000 (factor 1/metros).
- **Precio y costo por metro** = precio/costo de bobina ÷ metros (los metros se parsean del nombre). Vender bobina completa da el mismo total (±centavos por redondeo).
- Corrido en **STAGING (207/209)** y **PROD (208/210)**. 2 excepciones: id 4939 "Bobina o Solenoide" (no es cable) y id 927 (tiene movimientos de stock → Odoo bloquea cambio de UdM).
- **Cron parcheado** (`_syscom_cost_to_uom`): cuando `uom_po_id != uom_id` (misma categoría), guarda `standard_price` **por metro** (costo ÷ metros) → la nocturna no regresa el costo a "por bobina".

### D. Búsqueda de productos tolerante a guiones (syscom 18.0.1.8.4 → .8.5)
- Problema: `default_code` con guiones (`PRO-CAT-5E`) no se encontraba al teclear `procat5e`.
- Fix: campo **`code_normalized`** (código sin guiones/espacios, minúsculas, indexado) en `product.template` y `product.product` + override `name_search` que mezcla los resultados normalizados con el buscador nativo. Verificado en prod.

### E. Otra línea de trabajo (NO de esta sesión, en paralelo)
Hay commits `feat(coc)`/`docs(releases)` del **Portal COC Sprint-02** (WS-5 auth: handshake sesión efímera, OTP desacoplado, contraseñas Argon2, sesiones/dispositivos/magic links, integración EvoApi como proveedor OTP real). Workstream aparte; ver `releases/`.

---

## Pendientes para la próxima sesión
1. **Botón "Ver y Pagar en Línea":** no hay pasarela de pago activa. Decidir: activar una (Mercado Pago / Stripe / Conekta, con credenciales) **o** relabelar a "Ver factura en línea" mientras tanto.
2. **Verificar el QR de Telegram inline en Gmail** (prueba enviada a alarmassentinela@gmail.com). Si sale como adjunto, pasar el correo a `multipart/related`.
3. **Folio 00171 reusado / acuse perdido:** acuse de cancelación de 12458E1C solo en portal Prodigia. Evaluar política para no borrar facturas con CFDI (aunque sea cancelado).
4. **Go-live facturación (≈1-jul):** reactivar crones id 39/55/56 (ver [[project_email_freeze_migracion]]).
5. **Bobina id 927** (305m Cat5e, con stock): migrar a metro = archivar + crear nueva, o limpiar su historial de inventario. Y **bobinas nuevas de Syscom** entran como "Units" (correr esta migración periódicamente o configurar auto).
6. **Decimales del precio de bobina:** si quieren que vender bobina completa dé el total EXACTO, subir decimales del precio por metro.
7. **Lista de facturas:** el "Send" nativo masivo de Odoo (en la vista lista) sigue visible — ocultarlo si se quiere.
8. **Limpieza opcional** de los 163 mail.mail en `cancel`; `sentinela_subscriptions/__manifest__.py` sin clave `license` (warning menor).

## Verificaciones reales hechas
- Cancelación de Rocío: confirmada por respuesta del SAT (statusOk/201/cancelados=1).
- Timbre 404 (Rocío) y 399 (00169): timbrados válidos, XML correcto (PPD, total, descripción por mes / clave 26111701).
- Formato: render HTML confirmó cobranza@/régimen/uso(G03-desc)/condiciones(Crédito)/banco(Banorte vs HSBC)/notas en banda/sin referencia/botones PDF+pago.
- Envíos por `ir.mail_server` con message-id; wizard de envío probado (a egarza@) con destinatarios manuales.
- Bobinas: UdM y precio/costo por metro verificados en prod (ej. 152 m → $52.21/m, costo $29.99/m); helper del cron convierte costo/metro OK.
- Búsqueda sin guiones verificada en prod (000-15641-001 ← "00015641001").
- **Sin validar:** render inline del QR específicamente en Gmail (cliente real); el botón "pago en línea" sin pasarela activa.
