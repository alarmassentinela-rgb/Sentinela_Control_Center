# sentinela_subscriptions

Módulo **corazón** de Sentinela. Reemplaza a MASadmin/Argus como sistema de facturación recurrente + provisioning técnico (internet PPPoE/static, monitoreo de alarmas, GPS). Es `application: True`.

> Este archivo se auto-carga al trabajar en el módulo. Documenta el **cómo es el código** (arquitectura, trampas). El **estado/decisiones** del proyecto vive en la memoria (`MEMORY.md`), no aquí. Si cambias algo estructural, actualiza este archivo.

- **Versión actual:** ver `__manifest__.py` (`version`). Hoy `18.0.1.3.86`.
- **Odoo:** 18 Community. **DB prod:** V18 · **DB lab:** Sentinela_STAGING (`odoo-lab` :8075).
- **Deploy:** el server NO es git working tree. Usar skill `release-modulo` (bump+commit+tag+push) y luego `deploy-modulo` (rsync→`-u` STAGING→`-u` V18→verificar). Saltar rsync = el `-u` corre código viejo.

## Dependencias (manifest)
`base, mail, product, account, sale, sentinela_digital_sign, sentinela_cfdi_prodigia, om_account_followup`

- `sentinela_cfdi_prodigia` → timbrado CFDI. Las suscripciones "no timbrar" generan **remisión**, no factura; el gancho de cobro adelantado está en `action_post` (account.move), NO en el flujo CFDI, para que funcione igual con o sin timbre.
- `sentinela_digital_sign` → firma del contrato (`sign_document_id`, `action_send_contract_for_signature`).
- `om_account_followup` → recordatorios de cobranza (vista `res_partner_followup_es.xml`).

## Modelos (models/)
| `_name` | Archivo | Rol |
|---|---|---|
| `sentinela.subscription` | subscription.py (117KB, el grande) | Suscripción/contrato. Núcleo. |
| `sentinela.contract.template` (+`.preview`) | contract_template.py | Plantillas de contrato HTML. Motor = `mail.render.mixin` → **`inline_template`, solo `{{ }}`** (no Jinja `{% %}`). |
| `sentinela.mikrotik.profile` | mikrotik_profile.py | Perfil PPPoE/queue del MikroTik. |
| `sentinela.router` | router.py | Router/CCR destino del provisioning (incluye `pppoe_server_name`). |
| `sentinela.flolive.service` | flolive_service.py | SIM floLIVE (datos GPS). SMS por GraphQL. |
| `sentinela.senticar.service` | senticar_service.py | Dispositivo en SentiCar/Traccar. |
| `sentinela.subscription.gps.device` | gps_device.py | Equipo GPS (multi-equipo por sub). |
| `sentinela.service.definition` / `.product.service.inclusion` / `.subscription.service.inclusion` | service_matrix.py | Matriz: qué servicios (internet/alarma/gps) incluye cada plan. Se derivan al crear la sub. |
| inherit `res.partner` | res_partner.py | Cliente: datos fiscales/CFDI, `display_name`. |
| inherit `product.template` | product.py | Plan: modo de servicio, intervalo. |
| inherit `res.config.settings` | res_config_settings.py | Ajustes del módulo. |
| inherit `sale.order` / `sale.order.line` / `account.move` | subscription.py (final) | Ventas→sub y **cobro adelantado** (ver abajo). |

## Campos de estado clave (subscription.py)
- **`state`** (contrato/comercial): `draft → pending_signature → confirmed → active → suspension → closed / cancelled`.
- **`technical_state`** (red): `active` / `suspended` (falta de pago) / `cut` (retiro definitivo). Es lo que decide el provisioning real en el router.
- **`billing_mode`**: `normal` (factura, entra a cobranza/suspensión) vs `courtesy` (activo pero NO factura, NO cobranza, NO recordatorios, NO auto-suspensión). Solo manager lo edita (`_assert_billing_mode_manager`).
- **`recurring_interval`** + ciclo multi-mes → ver "Modelo de facturación" abajo.
- Secuencia: `SUB-####` (`ir_sequence_data.xml`).

## Crones (data/ir_cron_data.xml) — método en subscription.py
| Cron (id) | Método | Cadencia | Qué hace |
|---|---|---|---|
| `ir_cron_generate_invoices` | `_cron_generate_pre_invoices` | 1 día | Genera pre-facturas del ciclo. |
| `ir_cron_check_extensions` | `_cron_check_expired_extensions` | 1 hora | Cierra prórrogas vencidas. |
| `ir_cron_auto_suspend_overdue` | `_cron_auto_suspend_overdue` | 1 día | Suspende por facturas vencidas. |
| `ir_cron_send_payment_reminders` | `_cron_send_payment_reminders` | 1 día | Recordatorios de cobranza. |
| `ir_cron_check_leasing_end` | `_cron_check_leasing_end` | 1 día | Fin de leasing de equipo. |
| `ir_cron_refresh_antenna_signal` | `_cron_refresh_antenna_signal` | 15 min | Refresca conexión/señal de antena (WISP). |

> ⚠️ **Freeze de facturación activo** hasta go-live ≈1-jul: varios de estos crones están OFF en prod a propósito (ver memoria `project_email_freeze_migracion`). No los des por activos.

## Flujos importantes
- **Provisioning red:** `action_provision_mikrotik_enable/disable` → API MikroTik (`_get_mikrotik_api`). Suspensión WISP = **walled-garden** (deja el secret habilitado + perfil `argusblack_servicio_suspendido`), NO deshabilita el secret.
- **GPS:** `action_provision_senticar` (registra IMEI en Traccar), `_flolive_set_all` (corta/activa SIM), `action_send_gps_sms` (GraphQL floLIVE), `action_refresh_gps_diag`.
- **Contrato:** `_compute_contract_body_html` renderiza la plantilla; `action_send_contract_for_signature` → firma digital; `report/contract_report.xml`.
- **Cobro adelantado (account.move):** `_advance_on_post` empuja `next_billing` al publicar; `_advance_on_unpost` lo revierte al cancelar/nota de crédito. La alarma cobra **precio del periodo** (productos -3/-6/-12, qty=1); internet/gps cobran **tarifa mensual × meses del ciclo**. Dos caminos: **legacy** mono-suscripción (basado en líneas) y **global** del cliente (basado en metadatos). Ver sección **Cobro adelantado global** abajo.
- **post_init_hook** (`hooks.py`): carga plantillas base de contrato (INTERNET, MONITOREO) si no existen.

## Cobro adelantado global (del cliente) — D1–D3

Permite que un cliente **con varias suscripciones** prepague **N ciclos** de **todas** sus subs en **una sola factura**, incluso antes de que el cron genere su factura del mes. Convive con el adelanto **legacy** mono-suscripción sin romperlo.

### Modelos / campos (clase `account.move` en subscription.py)
- `subscription_ids` (M2M `account_move_subscription_rel`): todas las subs que aporta la factura (también lo usa la facturación global del cron). `subscription_id` (Many2one) se conserva solo cuando hay una sub (compatibilidad vistas/One2many).
- `advance_periods` (Integer): **nº de ciclos** que adelanta la factura. `>0` ⇒ es un adelanto **global** (`_is_global_advance()`). Es la **única** fuente del avance.
- `advance_detail` (Text/JSON): **snapshot** escrito al publicar — por sub `{sub_id, sub, interval, periods, months, old_date, new_date}`. Base de la reversa y la auditoría **sin leer las líneas**.
- `advance_executed_on` / `advance_executed_by`: auditoría (cuándo / quién).
- `advance_months_applied` (Integer): solo el camino **legacy** (meses empujados, para revertir exacto).

### Fuente única de líneas/cantidades (decisión #7, NO duplicar)
- `subscription._billing_line_qty(n_ciclos=1)` → cantidad de **una** sub para N ciclos (alarma/dominio = 1×N a precio de periodo; internet/mant = intervalo×N; gps = intervalo×equipos×N).
- `subscription._build_group_lines(subs, n_ciclos=1)` → comandos de línea de la factura de grupo. Lo usan **el cron** (`_billing_generate_invoice`, n=1), **el adelanto global** (n=N) y **el preview del wizard**. La **presentación** sigue `partner.invoice_grouping_method`: consolida para `global`, itemiza por sub para `individual`/`by_branch` — pero siempre es **una sola factura** con todas las subs.
- `subscription._billing_period_label(n_ciclos=1)` → etiqueta de periodo (mes único o rango de N×intervalo meses). La usan la descripción de línea Y el candado anti-duplicado del cron.

### Flujo de ejecución
1. **Wizard** `sentinela.subscription.advance.global.wizard` (lanzable desde el header de la suscripción y desde el form del cliente, botón "Cobro Adelantado Global"). Toma las subs del cliente en estado **`active` o `suspension`** no-cortesía (`_eligible_subs`; la suspendida por mora también puede prepagar y se reactiva al pagar; aplica igual a clientes de factura y de **remisión**), pide `n_ciclos`, y muestra el **preview** como una **tabla HTML calculada** (`preview_html`, campo `compute` — NO un One2many: el cliente web no renderizaba bien los comandos x2many del transient) con fecha de cobro ANTES/DESPUÉS por sub + aviso si hay **intervalos mixtos**.
2. **Bloqueo anti-concurrencia** `account.move._check_no_concurrent_global_advance(partner, subs)`: rechaza si ya hay un adelanto global **en curso** sobre esas subs (en `draft`, o `posted` no liquidado). Un adelanto ya pagado NO bloquea (encadenar es válido).
3. `action_create_invoice` crea la factura **borrador** (`is_advance_payment=True`, `advance_periods=N`, `subscription_ids=subs`, líneas de `_build_group_lines`). NO la publica.
4. **Al publicar** (`action_post` → `_advance_on_post`, camino global): cada sub avanza `N × su recurring_interval` meses; se escribe el snapshot + auditoría. El cron deja de tomarlas (su `next_billing_date` quedó en el futuro).
5. **Reversa total** (`button_draft`/`button_cancel` → `_advance_on_unpost`): lee el snapshot y regresa cada sub exactamente los meses aplicados.

### Idempotencia (garantía central)
- Candado `is_renewal_processed` (Boolean, `copy=False`). `_advance_on_post` se rinde si ya está `True` ⇒ **una factura nunca adelanta dos veces**, aunque `action_post` se redispare. `_advance_on_unpost` solo actúa si está `True` y lo apaga ⇒ **nunca revierte de más**.
- El avance es **determinístico** (`advance_periods × intervalo`, función pura de metadatos), no un acumulador. La reversa usa el **snapshot** (meses exactos por sub), no recálculo ni el M2M actual ⇒ es el inverso exacto del avance aunque el grupo cambie después.

### Limitaciones de V1 (por diseño)
- **Reversa ÚNICAMENTE total.** No hay notas de crédito parciales sobre un adelanto global: cualquier `out_refund` cuyo `reversed_entry_id` sea un adelanto global lanza `UserError` (revertir = cancelar la factura completa). La reversa parcial queda **fuera de alcance**.
- El adelanto abarca **todas** las subs activas del cliente (no subset).
- Overdue: adelantar N ciclos de una sub muy atrasada puede no llevar su fecha más allá de hoy (sigue debiendo el rezago) — comportamiento esperado.

### Decisiones de diseño (contexto que no se debe perder)
- **N = ciclos, no meses:** cada sub avanza según **su propio** intervalo (mensual/trimestral/anual).
- **El avance NO se lee de las líneas:** vive en metadatos explícitos (`advance_periods` + snapshot). Las líneas son solo el documento de cobro.
- **Camino legacy intacto:** el adelanto mono-sub (`subscription_id`, basado en líneas, con notas de crédito parciales) sigue funcionando; el global es un camino aparte marcado por `advance_periods>0`.
- **Una sola implementación de facturación** (decisión #7): cron y adelanto comparten `_build_group_lines`/`_billing_line_qty`; no hay dos caminos de cálculo.
- Construido en etapas reversibles **D1** (extracción de `_build_group_lines`), **D2** (motor de avance por metadatos + M2M + idempotencia + bloqueo de reversa parcial), **D3** (wizard + preview + bloqueo de concurrencia). Validado en STAGING por `odoo shell` end-to-end; **UAT en interfaz pendiente** antes del `-u` en prod.

## Trampas conocidas
- Plantillas de contrato: **solo `{{ }}`** (inline_template). `{% if %}` NO funciona — usar campos `_compute_*` que arman el HTML (ej. `_build_equipment_clause`).
- `default_recurring_interval` del producto **no se mantiene**, no confiar en él para el cálculo del ciclo.
- Cortesía (`billing_mode=courtesy`) debe saltar TODO el ciclo de cobranza, no solo la factura.
- Suspensión WISP nunca deshabilita el secret PPPoE (si lo haces, Argus/el cliente quedan inconsistentes) — usar walled-garden.
- `subscription.py` mezcla 5 clases (subscription + sale.order/line + account.move). Al buscar un método confirma en qué clase cae (los `_advance_*` y `action_post` son de **account.move**, no de la sub).

## Wizards (wizard/)
close · extension · transfer · advance (cobro adelantado mono-sub) · **advance_global (cobro adelantado global del cliente)** · generate_confirm · selection · mikrotik_traffic · gps_device_transfer.

## Controllers
`senticar_transportista.py` → portal público del transportista (links de rastreo temporales).
