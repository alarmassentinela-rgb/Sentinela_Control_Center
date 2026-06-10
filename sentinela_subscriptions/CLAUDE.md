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
- **Cobro adelantado (account.move):** `_advance_on_post` empuja `next_billing` al publicar; `_advance_on_unpost` lo revierte al cancelar/nota de crédito. La alarma cobra **precio del periodo** (productos -3/-6/-12, qty=1); internet/gps cobran **tarifa mensual × meses del ciclo**.
- **post_init_hook** (`hooks.py`): carga plantillas base de contrato (INTERNET, MONITOREO) si no existen.

## Trampas conocidas
- Plantillas de contrato: **solo `{{ }}`** (inline_template). `{% if %}` NO funciona — usar campos `_compute_*` que arman el HTML (ej. `_build_equipment_clause`).
- `default_recurring_interval` del producto **no se mantiene**, no confiar en él para el cálculo del ciclo.
- Cortesía (`billing_mode=courtesy`) debe saltar TODO el ciclo de cobranza, no solo la factura.
- Suspensión WISP nunca deshabilita el secret PPPoE (si lo haces, Argus/el cliente quedan inconsistentes) — usar walled-garden.
- `subscription.py` mezcla 5 clases (subscription + sale.order/line + account.move). Al buscar un método confirma en qué clase cae (los `_advance_*` y `action_post` son de **account.move**, no de la sub).

## Wizards (wizard/)
close · extension · transfer · advance (cobro adelantado) · generate_confirm · selection · mikrotik_traffic.

## Controllers
`senticar_transportista.py` → portal público del transportista (links de rastreo temporales).
