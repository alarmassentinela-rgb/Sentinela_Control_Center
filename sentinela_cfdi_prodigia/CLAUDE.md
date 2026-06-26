# sentinela_cfdi_prodigia

Timbrado de CFDI 4.0 para Odoo 18 Community a través del PAC **Prodigia** (PADE). Construye el XML del comprobante a mano (sin `l10n_mx_edi` de Enterprise), lo envía a Prodigia para sellarlo/timbrarlo y guarda UUID, sellos y QR en la factura. Es **dependencia de `sentinela_subscriptions`** (de ahí salen los campos `invoice_payment_method`/`invoice_payment_form` del partner que este módulo consume).

> Este archivo se auto-carga al trabajar en el módulo. Documenta el **cómo es el código** (arquitectura, trampas). El **estado/decisiones** del proyecto vive en la memoria (`MEMORY.md`), no aquí. Si cambias algo estructural, actualiza este archivo.

- **Versión actual:** ver `__manifest__.py` (`version`). Hoy `18.0.1.1.14`.
- **Odoo:** 18 Community. **DB prod:** V18 · **DB lab:** Sentinela_STAGING (`odoo-lab` :8075).
- **Deploy:** skill `release-modulo` (bump+commit+tag+push) y luego `deploy-modulo` (rsync→`-u` STAGING→`-u` V18→verificar). El server (192.168.3.2) NO es git working tree; sin rsync el `-u` corre código viejo.

## Dependencias (manifest)
`depends = ['account', 'base']`. Solo Odoo base + Contabilidad Community. NO usa `l10n_mx_edi` (Enterprise): todos los campos SAT (`l10n_mx_edi_*`) son redefinidos aquí como campos propios sobre `res.partner`, `res.company`, `account.tax`, `product.template` y `account.move`. `sentinela_subscriptions` depende de ESTE módulo, no al revés.

## Modelos (models/)
| `_name` / `_inherit` | Archivo | Rol |
|---|---|---|
| `_inherit account.move` | `account_move.py` | Núcleo: campos CFDI, generación del XML 4.0, llamada a Prodigia, extracción de timbre, QR, descarga XML. |
| `_inherit account.payment.register` | `account_move.py` | Forma de pago SAT al registrar cobro; la propaga a las facturas conciliadas. |
| `_inherit account.tax` | `account_tax.py` | `l10n_mx_edi_tax_code` (001 ISR / 002 IVA / 003 IEPS, default 002). |
| `_inherit product.template` | `product.py` | `l10n_mx_edi_code_sat` (ClaveProdServ) y `l10n_mx_edi_um_code_sat` (ClaveUnidad, default E48). |
| `_inherit res.company` | `res_company.py` | `l10n_mx_edi_fiscal_name` (razón social SAT) + régimen fiscal del emisor. |
| `_inherit res.config.settings` | `res_config_settings.py` | Credenciales/endpoint Prodigia → `ir.config_parameter`. |
| `_inherit res.partner` | `res_partner.py` | Régimen fiscal + Uso CFDI del receptor (catálogos SAT). |
| `_name sentinela.sat.payment.method` | `sat_catalogs.py` | Catálogo Formas de Pago SAT (modelo, casi sin uso; las selecciones reales viven inline en `account_move.py`). |
| `_inherit stock.picking` | `stock_picking.py` | Genera Nota de Crédito desde una devolución (NO timbra; usa el wizard estándar `account.move.reversal`). |

## Campos de estado clave (account.move)
- **`cfdi_status`** Selection: `draft` (Borrador) · `pending` (Pendiente de Timbrado) · `valid` (Timbrado Válido) · `cancel` (Cancelado) · `error` (Error). Default `draft`, `tracking=True`.
  - `cancel` lo asigna `action_cfdi_cancel_prodigia` cuando el SAT acepta la cancelación (ver §Cancelación).
- **`cfdi_uuid`** Char: folio fiscal. Es el discriminador FACTURA vs REMISIÓN en el reporte.
- **`cfdi_xml` / `cfdi_pdf`** Binary (attachment): XML/PDF timbrados; `*_filename` el nombre.
- **`cfdi_message`** Text: último mensaje/código del PAC o error de proceso.
- Datos para el PDF: `l10n_mx_edi_cfdi_certificate_serial_number`, `l10n_mx_edi_cfdi_timestamp`, `l10n_mx_edi_cfdi_seal` (sello del comprobante), `l10n_mx_edi_cfdi_sat_seal`, `l10n_mx_edi_cfdi_original_chain`, `l10n_mx_edi_cfdi_qr` (compute).
- **`l10n_mx_edi_payment_method_id_code`** Selection (Forma de Pago SAT) en `account.move` y en `account.payment.register`.

## Integración Prodigia (PAC)
- **Endpoint:** config param `sentinela_cfdi_prodigia.api_url`, default `https://facturacion.pade.mx/api/v1`.
- **Credenciales (NO copiar aquí):** Ajustes → res.config.settings, persistidas como `ir.config_parameter`:
  `sentinela_cfdi_prodigia.user`, `.password`, `.contract`, `.client_code`, `.rfc`, `.test_mode` (bool, default True), `.api_url`. Las lee `_get_prodigia_config()`.
- **Método de timbrado:** `action_cfdi_stamp_prodigia()` (alias `action_prodigia_stamp()` por compat de vistas en DB).
  - Exige `move.state == 'posted'` y que existan url/user/password/contract.
  - `_generate_cfdi_xml()` arma el `cfdi:Comprobante` 4.0 con lxml (Sello/NoCertificado/Certificado vacíos → los calcula el PAC).
  - POST JSON con HTTP Basic auth `(user, password)`, payload `{xmlBase64, contrato, prueba, opciones:["CALCULAR_SELLO"]}`, `timeout=30`.
- **Respuesta:** Prodigia responde **XML, no JSON**. Se parsea `timbradoOk`/`mensaje`/`codigo`; si OK, se decodifica `xmlBase64`/`xml` y se extrae el nodo `TimbreFiscalDigital` (UUID, NoCertificadoSAT, FechaTimbrado, SelloSAT, SelloCFD, RfcProvCertif). La cadena original se reconstruye a mano (`1.1||UUID||...||`).
- **Manejo de errores:** todo el flujo va en `try/except`; cualquier fallo (HTTP ≠200/202, sin TFD, excepción) escribe `cfdi_status='error'` + `cfdi_message`. NO relanza excepción al usuario (salvo las validaciones previas de RFC/régimen, que sí son `UserError`).
- **Cancelación:** `action_cfdi_cancel_prodigia(motivo, folio_sustitucion)` (botón "Cancelar ante el SAT" → wizard `sentinela.cfdi.cancel.wizard`). Endpoint **`cancelacion/cancelar`** (config `sentinela_cfdi_prodigia.cancel_url`), **POST con query params** (no GET → da 405): `contrato`, `rfcEmisor`, `arregloUUID='UUID|motivo|folioSustitucion'` (3 campos) y **`opciones=CERT_DEFAULT`** (usa el CSD del contrato; SIN `CERT_DEFAULT` pide "contraseña del archivo"). Respuesta XML `<servicioCancel>`: `statusOk` + `<cancelacion><codigo>` por UUID (**201**=aceptada, **202**=ya cancelada, **205**=no existe) + `acuseCancelBase64`. Éxito = `statusOk && (codigo in 201/202 || cancelados>0)` → `cfdi_status='cancel'` + guarda acuse en `cfdi_cancel_acuse`. NO borra el XML timbrado original. Motivo **01** exige `folio_sustitucion` (UUID que reemplaza). ⚠️ El endpoint `integracion/cancelarCfdiConOpciones` NO funcionó (no reconoce el arreglo de folios); usar `cancelacion/cancelar`.
- **Candado anti-doble-timbrado:** `action_cfdi_stamp_prodigia` lanza UserError si la factura ya tiene `cfdi_uuid` y `cfdi_status='valid'` (hay que cancelar antes de re-timbrar).
- **Consulta de estatus:** NO implementada.

## Crones (data/ir_cron_data.xml)
- **`ir_cron_auto_stamp_prodigia`** → `account.move._cron_auto_stamp_prodigia()` (cada 1h). **Nace DESACTIVADO** (`active=False`, `noupdate="1"` para que activarlo no se revierta en `-u`). Auto-timbra facturas **nuevas** con triple salvaguarda:
  1. Gate global: solo corre si `ir.config_parameter` `sentinela_cfdi_prodigia.auto_stamp_enabled == '1'` (default `0`).
  2. Corte por fecha: dominio `invoice_date >= sentinela_cfdi_prodigia.auto_stamp_cutoff` (default `2026-06-25`) → NO toca facturas anteriores.
  3. Dominio: `out_invoice` + `state='posted'` + `cfdi_status='pending'` + `cfdi_uuid=False` (las remisiones de clientes 'no timbrar' nacen `cfdi_status='draft'` y nunca entran).
  - Lote `auto_stamp_batch` (default 50), `order='invoice_date, id'`, **commit por factura** (un error deja esa en `error` y sigue con el resto; no reintenta las que quedan en `error`).
  - El modo prueba/real lo sigue rigiendo `test_mode` (NO lo cambia el cron).
  - **Para activarlo:** poner `auto_stamp_enabled=1` y activar el cron. El timbrado MANUAL (`action_cfdi_stamp_prodigia`) sigue disponible siempre.

## Reporte factura/remisión
- **`report_invoice.xml`** (cargado en manifest): paperformat carta + `report.action account.account_invoices` reasignada + plantilla **`report_invoice_cfdi_section`** que `inherit_id="account.report_invoice_document"` y **reemplaza** el layout (`web.external_layout` → `web.basic_layout`).
- Una sola plantilla condicional por **`cfdi_uuid`**: `doc_label = 'FACTURA' if o.cfdi_uuid else 'REMISIÓN'` (timbrada = factura; sin timbrar = remisión interna).
- **Emisor** = razón social fiscal de la persona física: `o.company_id.l10n_mx_edi_fiscal_name or o.company_id.name` (la marca "Sentinela" queda solo en el logo).
- Tasa IVA tomada de la línea real (8% frontera u 16%), no hardcodeada. Logo vía `_get_company_logo_b64()`, QR vía `_get_cfdi_qr_b64()`.

## Flujos importantes
- **Timbrar:** factura `posted` → botón → `action_cfdi_stamp_prodigia` → genera XML → POST a Prodigia → guarda UUID/sellos → `cfdi_status='valid'`.
- **Forma de pago SAT:** al registrar pago (`account.payment.register._create_payments`) se copia `l10n_mx_edi_payment_method_id_code` a las facturas conciliadas.
- **Devolución → Nota de Crédito:** `stock.picking.action_generate_credit_note_from_return()` localiza la venta/factura origen, reversa con `account.move.reversal`, recorta líneas a lo realmente devuelto y vincula `credit_note_id`. NO timbra la NC.
- **Descarga XML:** `action_download_cfdi_xml()` → URL `/web/content/account.move/<id>/cfdi_xml/...`.

## Trampas conocidas
- **Fecha en hora local hardcodeada:** `Fecha` del comprobante = `datetime.now() - 6h - 5min` (CST fijo + margen). No respeta DST ni otra zona; revisar si cambia el huso.
- **`prueba`/`test_mode` default True:** mientras `sentinela_cfdi_prodigia.test_mode` sea True, los timbres son de PRUEBA (no válidos ante SAT). Hay que desactivarlo explícitamente en prod.
- **Prodigia responde XML, no JSON** — no asumir JSON al tocar el parseo de respuesta.
- **`Descripcion` reemplaza `|`→`/`** a propósito: el pipe es separador de la cadena original del CFDI y la rompería.
- **Cancelación = POST + CERT_DEFAULT:** el endpoint `cancelacion/cancelar` rechaza GET (405) y sin `opciones=CERT_DEFAULT` pide la contraseña del CSD. La leyenda "DOCUMENTO DE PRUEBA" del PDF NO indica timbre de prueba (estaba hardcodeada; hoy condicionada a `test_mode`).
- **Dos plantillas de reporte en disco, solo una activa:** `report_invoice_document_inherit.xml` (plantilla `report_invoice_document_cfdi_inherit`) NO está en el manifest `data` → no se carga. La activa es `report_invoice.xml`. No confundirlas.
- **El XML se construye a mano** (sin `l10n_mx_edi`): cualquier cambio de catálogo/atributo SAT se edita en `_generate_cfdi_xml`. La línea de `TasaOCuota` se setea dos veces (la última, `:.6f`, es la que vale).
- **Campos del partner externos:** `invoice_payment_method`/`invoice_payment_form` (PUE/PPD/forma de pago) vienen de `sentinela_subscriptions`, no de este módulo; se acceden con `hasattr`/`getattr` defensivo.
- **`sat_catalogs.py`** define el modelo `sentinela.sat.payment.method` pero las selecciones de forma de pago reales están inline en `account_move.py` (`SAT_PAYMENT_METHODS` y el campo en `account.move`); el modelo está prácticamente huérfano.

## Wizards / Controllers / Tests
- **Wizards:** `sentinela.cfdi.cancel.wizard` (`wizards/`) para cancelar ante el SAT (motivo + folio sustitución). Además reutiliza `account.move.reversal` estándar para NC.
- **Controllers:** ninguno (descarga vía `/web/content` nativo).
- **Tests:** ninguno.
- **Security:** `security/ir.model.access.csv` con un único ACL (`res.config.settings` para `base.group_system`).
