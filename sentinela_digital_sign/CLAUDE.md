# sentinela_digital_sign

Permite a clientes **firmar documentos PDF desde el portal web** (firma manuscrita capturada en canvas). El documento firmado se sella anexando una página de certificación al PDF. Es **dependencia de `sentinela_subscriptions`**: el contrato de la suscripción se firma con este módulo (`sign_document_id`, `action_send_contract_for_signature`).

> Este archivo se auto-carga al trabajar en el módulo. Documenta el **cómo es el código** (arquitectura, trampas). El **estado/decisiones** del proyecto vive en la memoria (`MEMORY.md`), no aquí. Si cambias algo estructural, actualiza este archivo.

- **Versión actual:** ver `__manifest__.py` (`version`). Hoy `18.0.1.0.0`.
- **Odoo:** 18 Community. **DB prod:** V18 · **DB lab:** Sentinela_STAGING (`odoo-lab` :8075).
- **Deploy:** el server NO es git working tree. Usar skill `release-modulo` (bump+commit+tag+push) y luego `deploy-modulo` (rsync→`-u` STAGING→`-u` V18→verificar). Saltar rsync = el `-u` corre código viejo.

## Dependencias (manifest)
`base, mail, portal, web`

- `portal` → `portal.mixin` (modelo hereda `access_url`/`access_token`), `t-call="portal.portal_layout"` y `t-call="portal.signature_form"` (el canvas de firma estándar de Odoo + su JS `js_accept_json_modal`).
- `mail` → `mail.thread`/`mail.activity.mixin` (chatter) y la plantilla de correo de solicitud de firma.
- `web` → visor PDF embebido (`pdf_viewer`, `/web/content`).

## Modelos (models/)
| `_name` | Archivo | Rol |
|---|---|---|
| `sentinela.sign.document` | sign_document.py | Documento a firmar. `_inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']`. Guarda PDF original (`file`), firmado (`file_signed`), imagen de la firma (`signature`), y enlace genérico al origen (`res_model`/`res_id`). |

Único modelo. No hay herencias de otros modelos en este módulo (la integración con la suscripción vive en `sentinela_subscriptions`).

## Campos de estado clave
`state` (Selection):
- `draft` — Borrador. Creado, PDF cargado, aún no enviado. Editable.
- `sent` — Enviado. `action_send_email` mandó el correo al cliente y abrió el acceso por portal. **Único estado en que el portal permite firmar.**
- `signed` — Firmado. Se capturó la firma y se generó `file_signed`.
- `cancel` — Cancelado.

Otros campos: `signed_by` (Char, nombre tecleado), `signed_on` (Datetime), `signature` (Binary, imagen). Secuencia `DOC-####` (`ir_sequence_data.xml`, code `sentinela.sign.document`).

## Controllers / Portal de firma
`controllers/portal.py` → clase `SignPortal(CustomerPortal)`. Todas las rutas son `auth="public"` + `website=True` y validan acceso con `self._document_check_access('sentinela.sign.document', doc_id, access_token=...)` (token del `portal.mixin`); fallo → redirige a `/my`.

| Ruta | type | Qué hace |
|---|---|---|
| `/my/document/<int:doc_id>` | http | Renderiza `portal_my_document_view` (visor PDF + botón Firmar). |
| `/my/document/<int:doc_id>/sign` | json | Recibe `name`+`signature`, valida `state == 'sent'`, llama `doc_sudo.action_sign({...})`. Devuelve `force_refresh`+`redirect_url`. |
| `/my/document/<int:doc_id>/download` | http | Descarga `file_signed` como `application/pdf` (`content_disposition`). |

Trampas de seguridad:
- Acceso **sin login** mediante `access_token` (cliente externo). El registro se usa en `sudo` (`doc_sudo`) tras pasar `_document_check_access`.
- `_compute_access_url` fija `access_url = '/my/document/%s'`; el correo usa `object.get_portal_url()` (anexa el token).
- La firma solo se acepta si `state == 'sent'` (en draft/signed/cancel responde error).

## Crones (data/...)
— (no hay crones; solo `ir_sequence_data.xml` y `mail_template_data.xml`).

## Flujos importantes
- **Enviar a firma:** `action_send_email()` → `message_post_with_source(template mail_template_sign_document_request)` con `email_layout` estándar → `state='sent'`. La plantilla incluye botón "Revisar y Firmar" con `object.get_portal_url()`.
- **Firmar:** ruta `/sign` (json) → `action_sign(signature)` guarda `signature`/`signed_by`/`signed_on`, genera el PDF firmado, pasa a `state='signed'`.
- **Sellar el PDF:** `_generate_signed_pdf()` crea con **ReportLab** (`canvas` + `letter`) una página "CERTIFICADO DE FIRMA DIGITAL" (referencia, firmante, fecha, cliente, imagen de la firma) y la **anexa al final** del original con `odoo.tools.pdf.merge_pdf([original, certificado])`. Resultado en `file_signed`.
- **Integración con subscriptions:** `action_sign` detecta `res_model == 'sentinela.subscription'`; si la sub está en `pending_signature`, la pasa a `confirmed` y postea en su chatter "Contrato firmado digitalmente". Del lado de la sub: `action_send_contract_for_signature` crea el `sentinela.sign.document` (PDF = `contract_body` codificado) y llama `action_send_email`; `sign_document_id`/`sign_state` enlazan ambos.

## Trampas conocidas
- **El "PDF" que envía la suscripción NO es un PDF real:** `action_send_contract_for_signature`/`action_request_signature` hacen `base64.b64encode(contract_body.encode('utf-8'))` — es HTML/texto codificado, no un PDF renderizado (comentario en el código: "Dummy PDF, en Odoo real usaríamos ir.actions.report"). El visor `pdf_viewer`/iframe puede no mostrarlo bien.
- **`merge_pdf` puede fallar** si el `file` original no es PDF válido (caso anterior). Hay fallback: `_generate_signed_pdf` captura la excepción, postea el error en el chatter y **no rompe el flujo**, pero `file_signed` queda vacío (la descarga devuelve `not_found`).
- **Incrustar la firma en ReportLab es frágil:** `can.drawImage(base64.b64decode(self.signature), ...)` pasa bytes crudos (ReportLab a veces espera path/ImageReader); hay `try/except` que cae a un texto `[Firma Digital Capturada]` si falla.
- El sellado **anexa una página de certificación**; NO estampa la firma sobre el documento original ni firma criptográficamente el PDF (no es PAdES/PKCS, es evidencia visual).
- Almacenamiento: `file`/`file_signed`/`signature` son `Binary attachment=True` (van a `ir.attachment`/filestore, no a columna de la tabla).

## Wizards / Static / Tests
- **Static:** no hay JS/CSS propio. El canvas de firma es el estándar de Odoo (`t-call="portal.signature_form"` con `call_url = .../sign` y `default_name`); el envío lo maneja `js_accept_json_modal` del módulo `portal`. El manifest declara `web.assets_frontend` vacío.
- **Wizards / Tests:** no existen.
- **Vistas backend:** `sign_document_views.xml` (form con botón "Enviar al Cliente", statusbar, visores PDF previa/firmado), tree, action; `menus.xml`.
- **Seguridad:** `ir.model.access.csv` — `base.group_user` RW/create/unlink total; `base.group_portal` solo lectura. `security.xml` sin reglas de registro.
