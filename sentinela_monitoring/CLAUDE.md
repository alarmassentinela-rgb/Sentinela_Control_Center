# sentinela_monitoring

Central de monitoreo de alarmas integrada en Odoo: recibe señales de receptores/paneles, las convierte en eventos atendibles por operadores (claim/SLA/bitácora), despacha patrullas y cierra con reporte al cliente. Es el reemplazo en desarrollo de **Securithor**.

> Este archivo se auto-carga al trabajar en el módulo. Documenta el **cómo es el código** (arquitectura, trampas). El **estado/decisiones** del proyecto vive en la memoria (`MEMORY.md`), no aquí. Si cambias algo estructural, actualiza este archivo.

- **Versión actual:** ver `__manifest__.py` (`version`). Hoy `18.0.1.7.0`.
- **Odoo:** 18 Community. **DB prod:** V18 · **DB lab:** Sentinela_STAGING (`odoo-lab` :8075).
- **Deploy:** usar skill `release-modulo` (bump `version` + commit + tag + push) y luego `deploy-modulo` (rsync local→server → `-u` en STAGING → `-u` en V18 → verificar). El server (192.168.3.2) NO es git working tree; **sin rsync el `-u` corre código viejo**.

## Dependencias (manifest)
| Depend | Por qué importa |
|---|---|
| `base`, `mail` | Modelos base; `alarm.event` usa `mail.thread` + `mail.activity.mixin` + `portal.mixin`. |
| `sentinela_subscriptions` | `monitoring.device` y eventos cuelgan de `sentinela.subscription`; estados de suscripción (activo/suspendido) condicionan la atención. |
| `sentinela_fsm` | Despacho de patrullas/técnicos vía `sentinela.fsm.order` (extendido aquí). |
| `sale_management`, `account` | Cobro de servicios extra (patrullaje): `_create_service_sale_order`. |
| `stock` | Dependencia declarada del manifest. |

## Modelos (models/)
| `_name` / `_inherit` | Archivo | Rol |
|---|---|---|
| `sentinela.alarm.event` (+ portal/mail mixins) | `alarm_event.py` | **Modelo central.** Evento atendible: claim de operador, SLA, cierre tipificado, reporte, grabaciones, despacho. |
| `sentinela.alarm.signal` | `alarm_signal.py` | Señal cruda recibida. Puede ir a cuarentena (cuenta no registrada) y promoverse a device. |
| `sentinela.monitoring.device` | `monitoring_device.py` | Panel/dispositivo monitoreado (cuenta, ubicación, video, protocolo). |
| `sentinela.monitoring.zone` | `monitoring_zone.py` | Zonas/particiones del panel. |
| `sentinela.monitoring.contact` | `monitoring_contact.py` | Contactos de llamado del sitio. |
| `sentinela.monitoring.call` | `monitoring_call.py` | Registro de llamadas (click-to-call / Asterisk). |
| `sentinela.monitoring.config` | `monitoring_config.py` | Configuración del módulo. |
| `sentinela.monitoring.device.share` | `monitoring_device_share.py` | Compartir dispositivo con cliente final. |
| `sentinela.alarm.code` | `alarm_code.py` | Catálogo de códigos (Contact-ID), prioridad y `requires_attention`. |
| `sentinela.alarm.code.template` / `.template.line` | `alarm_code_template.py` | Plantillas de códigos por tipo de panel. |
| `sentinela.alarm.priority` | `alarm_priority.py` | Prioridades + `sla_response_minutes`. |
| `sentinela.device.alarm.config` | `device_alarm_config.py` | Config de códigos por dispositivo. |
| `sentinela.response.team` | `response_team.py` | Equipos de respuesta. |
| `sentinela.receiver.status` | `receiver_status.py` | Heartbeat del receptor (última señal recibida). |
| `sentinela.service.authorization.token` | `service_authorization_token.py` | Token de autorización de servicio extra (patrulla) por enlace público. |
| `sentinela.fsm.order` (inherit) | `fsm_order_extension.py` | Extiende órdenes FSM para patrullaje. |
| `sentinela.subscription` (inherit) | `subscription_extension.py` | Campos de monitoreo en la suscripción. |
| `res.partner` (inherit) | `res_partner_extension.py` | Datos de monitoreo y telefonía del contacto (Telegram/WhatsApp/EvoApi, click-to-call AMI, GPS). |
| `res.users` (inherit) | `res_users.py` | Campos de operador/técnico. |
| `res.config.settings` (inherit) | `monitoring_settings.py` | Ajustes del módulo. |

## Campos de estado clave
**`sentinela.alarm.event.status`** (flujo del operador): `active` → `acknowledged` → `in_progress` / `paused` / `escalated` → `resolved` → `closed`.

**`sentinela.alarm.event.sla_status`** (computado, no almacenado): `no_sla` / `ok` / `warning` (≥50 % del tiempo) / `overdue` / `met` / `breached`. Para filtros usar el campo almacenado `sla_deadline`, no este.

**`sentinela.alarm.event.close_reason`** (tipificación obligatoria al cerrar): `false_alarm`, `user_error`, `customer_confirmed_ok`, `verified_real`, `patrol_no_event`, `patrol_event`, `no_contact`, `technical_fault`, `test_signal`, `auto_offline_recovered`, `cliente_rechazo_servicio`, `other`.

**`sentinela.alarm.signal.status`**: `received` → `processing` → `acknowledged` → `assigned` → `in_progress` → `resolved` → `closed`.

**`sentinela.service.authorization.token.state`**: `pending` / `authorized` / `rejected` / `cancelled`.

**`sentinela.alarm.event.subscription_state`** (computado): `active` / `suspended` / `cut` / `none`.

## Crones (data/monitoring_cron_data.xml) — métodos en `alarm_event.py`
Definidos como `ir.actions.server` (state=`code`) + `ir.cron`, dentro de `<data noupdate="1">`.

| Cron (id) | Método | Cadencia | Qué hace |
|---|---|---|---|
| `ir_cron_sync_ucm_recordings` | `_cron_fetch_ucm_recordings()` | 10 min | Descarga grabaciones de llamadas de la central UCM/Asterisk y las adjunta al evento. |
| `ir_cron_detect_offline_panels` | `_cron_detect_offline_panels()` | 1 hora | Detecta paneles sin comunicación y abre evento marcado `[AUTO_OFFLINE]`. |
| `ir_cron_release_stale_locks` | `_cron_release_stale_locks()` | 2 min | Libera el claim (`current_operator_id`) de eventos cuyo `claimed_at` supera `LOCK_TIMEOUT_MINUTES` (15). |

## Flujos importantes
- **Ingesta (Fórmula 1):** `process_signal_from_receptor(vals)` hace todo en una llamada — busca el device por `account_number`; si no existe crea una **señal en cuarentena** (no crea device ni event); si existe actualiza `last_communication`, auto-resuelve un trouble `[AUTO_OFFLINE]` abierto, resuelve código→prioridad (default `35`), crea evento solo si el código `requires_attention`, crea la señal siempre, notifica al `bus.bus` (canal `sentinela_monitoring`) y refresca `receiver.status.last_heartbeat`.
- **Entrada de señales:** el receptor vivo (`sentinela_receiver`, `receiver_v6.py`) entra por **XML-RPC** llamando `sentinela.alarm.event.process_signal_from_receptor`. NO hay endpoint HTTP de ingesta (los antiguos `/api/monitoring/signal` y `/api/alarm/signals` se eliminaron en 14-jun-2026: estaban rotos —API vieja, sin auth real— y solo los usaban receivers en `_legacy/`).
- **Claim / mutex de operador:** `action_claim_event` / `_try_claim` / `action_release_event` / `action_force_release`; `_ensure_claim_held` protege escrituras. `_compute_lock_state` deriva `is_locked_by_other` / `can_release`.
- **Atención del evento:** `action_acknowledge`, `action_escalate`, `action_assign_technician`, `action_resolve`, `action_close`.
- **Servicio extra (patrulla) con cobro:** `action_request_service_authorization` → token público (`/sentinela/autorizar/<token>`) → `action_authorize_service` → `_create_service_sale_order` → `create_fsm_order` (orden FSM de patrullaje).
- **Reportes/cierre al cliente:** `_render_master_report_pdf`, `action_send_closure_report`, `action_send_master_report`; `action_capture_snapshot` para videoverificación (si `device.has_video`).
- **Portal del cliente:** `/my/eventos`, `/my/eventos/<id>`, `/my/eventos/<id>/pdf` (`controllers/portal_events.py`).

## Trampas conocidas
- **`post_init_hook` parchea SQL crudo `view_mode` 'tree'→'list'** (Odoo 18 renombró `tree`→`list`), incluido un fix hardcodeado para la acción `id=589`. Si clonas/migras vistas a otra DB ese id puede no aplicar; el hook es defensivo, no rompe si no encuentra match.
- **Prioridad default `35`** está hardcodeada en `process_signal_from_receptor` (es un id de `sentinela.alarm.priority`). Si esa prioridad no existe en una DB nueva, los eventos sin código mapeado fallarán o quedarán sin prioridad — verificar `alarm_codes_data.xml` / seeds.
- **Política de suspendidos (Opción C, 16-may-2026):** clientes suspendidos por mora **NO se auto-archivan**; el evento se crea igual y se muestra al operador con bandera (`subscription_state`). No reintroducir auto-archivado.
- **Cuarentena:** señales de cuentas no registradas NO crean device ni evento; quedan como `alarm.signal` con `is_quarantine=True` y requieren `action_promote_to_device` manual. No asumir que toda señal genera evento.
- **`sla_status` es computado no almacenado** (`store=False`): no usarlo en dominios de búsqueda; filtrar por `sla_deadline`.
- **Token de autorización expira a las `TOKEN_TTL_HOURS=48`** (`service_authorization_token.py`): `authorize`/`reject` hacen `SELECT … FOR UPDATE` (`_lock_and_guard`) para serializar respuestas concurrentes (anti doble-cobro) + validan expiración. Tokens creados ANTES de esta migración tienen `expiration_date` NULL → `is_expired()` es False (no expiran); es esperado.
- **Lock por inactividad:** `LOCK_TIMEOUT_MINUTES = 15` (constante en `alarm_event.py`); el cron de 2 min es quien lo libera. Cambiar la constante sin tocar el cron desincroniza la UX.
- **Reporte PDF / nombres:** `_clean_translated_name` y varios `replace('/', '_')` saneando nombres de archivo y de código — el render maneja cuentas sin registrar con literal `⚠️ CUENTA NO REGISTRADA`.
- **Secretos en `ir.config_parameter` (NO en el repo, desde 14-jun-2026):** las credenciales de telefonía/notificación se leen de Parámetros del sistema y deben estar **sembradas en prod y staging** o esas funciones se desactivan (fallan-seguro con warning, no rompen). Claves: `sentinela_monitoring.ami_password` (click-to-call AMI; host/port/user tienen default `192.168.3.5`/`7777`/`admin_ami`), `sentinela_monitoring.ucm_password` (sync grabaciones + dial contacto; host/user default `192.168.3.5:8089`/`odoo_api`), `sentinela_monitoring.evoapi_key` (WhatsApp), `sentinela_syscom.telegram_token` (Telegram). El helper `res.partner._get_ami_config()` centraliza el AMI (lo reusa `alarm.event.action_click_to_call`).

## Wizards / Controllers / Tests
- **Wizards** (`wizard/`):
  - `sentinela.alarm.handle.wizard` (+ `.contact.attempt`) — asistente multi-paso de atención: bitácora de intentos de contacto, atajos (`action_shortcut_false_alarm`, `action_shortcut_customer_ok`), solicitar/autorizar/despachar patrulla, crear ticket técnico, pausar/cerrar/finalizar evento (`_consolidate_bitacora`).
  - `sentinela.patrol.dispatch.wizard` — `action_dispatch` de la patrulla.
- **Controllers** (`controllers/`): `portal_events.py` (portal cliente), `service_authorization.py` (`/sentinela/autorizar/<token>`), `senticar_portal.py` (`/web/senticar/radar`, GPS SentiCar).
- **Tests:** no hay carpeta `tests/` en el módulo. (La memoria menciona pytest a nivel proyecto/sesiones; este addon no incluye su propia suite.)
- **Assets JS** (`static/src/js/`): `monitoring_dashboard.js` + `alarm_service.js` (dashboard de operador en tiempo real vía canal `bus.bus` `sentinela_monitoring`).
