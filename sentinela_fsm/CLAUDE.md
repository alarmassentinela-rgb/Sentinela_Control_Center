# sentinela_fsm

Módulo FSM (Field Service Management) de Sentinela: órdenes de servicio en campo (instalación, reparación, mantenimiento, traslado, retiro, patrullaje). Reemplazo de 2Worker/Auvo. Las ventas confirmadas generan órdenes automáticamente y el patrullaje se sigue en vivo vía Traccar/SentiCar.

> Este archivo se auto-carga al trabajar en el módulo. Documenta el **cómo es el código** (arquitectura, trampas). El **estado/decisiones** del proyecto vive en la memoria (`MEMORY.md`), no aquí. Si cambias algo estructural, actualiza este archivo.

- **Versión actual:** ver `__manifest__.py` (`version`). Hoy `18.0.1.5.1`.
- **Odoo:** 18 Community. **DB prod:** V18 · **DB lab:** Sentinela_STAGING (`odoo-lab` :8075).
- **Deploy:** usar skill `release-modulo` (bump+commit+tag+push) y luego `deploy-modulo` (rsync→`-u` STAGING→`-u` V18→verificar). El server (192.168.3.2) NO es git working tree; sin rsync el `-u` corre código viejo.

## Dependencias (manifest)
| Depend | Por qué importa |
|---|---|
| `base`, `mail` | Base; `mail.thread`/`mail.activity.mixin` en la orden (tracking, chatter). |
| `sale_management` | `sale.order._action_confirm` extendido genera las órdenes FSM al confirmar la venta. |
| `sentinela_subscriptions` | La orden se enlaza a `sentinela.subscription`; el cron de mantenimiento preventivo corre sobre ese modelo y lee `maintenance_frequency` / `next_maintenance_date` / `service_type` (tecnología). |
| `base_automation` | Acción automatizada `base.automation` que avisa al vendedor cuando una orden se pausa por cotización. |
| `stock` | `_create_stock_moves` mueve equipos/materiales usados en la orden. |
| Python `geopy` (externo) | `geopy.distance.geodesic` para optimización de rutas. (El cálculo ETA del patrullaje usa Haversine propio, no geopy.) |

## Modelos (models/)
| `_name` / `_inherit` | Archivo | Rol |
|---|---|---|
| `sentinela.fsm.order` (inherit `portal.mixin`, `mail.thread`, `mail.activity.mixin`) | fsm_order.py | Orden de servicio. Modelo central (~877 líneas). |
| `sentinela.fsm.work.log` | fsm_order.py / fsm_work_log.py | Bitácora de trabajo (registro de tiempos por etapa). |
| `sentinela.fsm.task.template` | fsm_checklist.py | Plantilla de tareas de checklist (por `service_type` y `tech_category`). |
| `sentinela.fsm.order.line` | fsm_checklist.py | Línea de checklist de la orden. |
| `sentinela.fsm.evidence` | fsm_evidence.py | Evidencia fotográfica/firma. |
| `sentinela.fsm.equipment` | fsm_equipment.py | Equipos/materiales usados (alimenta costo y stock moves). |
| `sentinela.fsm.chat.message` | fsm_chat.py | Mensajes de chat cliente-técnico. |
| `sentinela.fsm.notification` | fsm_notification.py | Notificaciones (push). |
| `sentinela.fsm.pause.reason` | fsm_pause_reason.py | Causas de pausa (incluye `is_quote_reason` para disparar cotización). |
| `sentinela.fsm.route.optimization` | fsm_route_optimization.py | Ruta optimizada del técnico. |
| `sentinela.fsm.route.line` | fsm_route_optimization.py | Línea/parada de la ruta. |
| `sentinela.fsm.dashboard` | fsm_dashboard.py | Tablero. |
| `product.template` (inherit) | product_template.py | Añade `generates_fsm_order` + `fsm_service_type`. |
| `sale.order` (inherit) | sale_order.py | `_action_confirm` crea órdenes FSM. |
| `sentinela.subscription` (inherit) | subscription.py | Cron mantenimiento + contadores de órdenes/evidencias. |
| `res.users` (inherit) | res_users.py | Contador de notificaciones FSM no leídas. |

## Campos de estado clave
**`sentinela.fsm.order.stage`** (Selection, default `new`, tracking):
`new` Nuevo · `assigned` Asignado · `in_progress` En Proceso · `paused` Pausado · `done` Finalizado · `cancel` Cancelado.

**`sentinela.fsm.order.service_type`** (Selection, default `other`) — tipo de orden:
`install` Instalación · `repair` Reparación/Falla (Correctivo) · `maintenance` Mantenimiento Preventivo · `transfer` Traslado · `removal` Retiro de Equipo/Desinstalación · `patrol` Patrullaje/Respuesta · `other` Otro.

**`sentinela.fsm.order.priority`**: `0` Normal · `1` Alta · `2` Urgente · `3` Crítica.

**`patrol_result`**: Selection con el resultado del patrullaje (campo en fsm_order.py).

**`product.template.fsm_service_type`** y el del wizard usan la constante `FSM_SALE_SERVICE_TYPES` definida en `product_template.py` (subconjunto de tipos vendibles, default `install`).

**`sentinela.fsm.route.optimization.status`**: incluye `optimized` (Optimizada), más estados de inicio/fin de ruta.

## Crones (data/...) 
| Cron (id) | Método | Cadencia | Qué hace |
|---|---|---|---|
| `ir_cron_generate_preventive_maintenance` (data/fsm_automation_data.xml) | `sentinela.subscription._cron_generate_preventive_maintenance()` (models/subscription.py) | cada 1 día | Busca subs `active` con `maintenance_frequency != '0'` y `next_maintenance_date <= hoy`, crea orden FSM `maintenance` (si no hay una abierta) y avanza `next_maintenance_date` por `relativedelta(months=...)` aunque ya existiera orden abierta (evita re-disparo diario). |
| `ir_cron_send_eta_updates` (data/fsm_patrol_data.xml) | `sentinela.fsm.order._cron_send_eta_updates()` (models/fsm_order.py) | cada 3 min | Para patrullas (`service_type='patrol'`) en `assigned`/`in_progress` sin `arrival_date` y con menos de `MAX_ETA_UPDATES_PER_ORDER` envíos, recalcula ETA y notifica al cliente. |

Nota: el aviso al vendedor por cotización NO es cron sino `base.automation` `auto_action_fsm_quote_needed` (trigger `on_write`): cuando la orden pasa a `paused` con `pause_reason_id.is_quote_reason = True`, ejecuta el server action que llama `notify_salesperson_for_quote()`.

## Flujos importantes
- **Ventas → orden (auto):** `sale.order._action_confirm` crea órdenes FSM según el caso: (1) `transfer` si la SO tiene `target_transfer_address_id`; (2) `repair` (urgente) si `origin` contiene "Reactivación"; (3) `install` inicial para líneas de suscripción nuevas — se omite si ya existe una sub activa/closed/suspended (renovación) o duplicado. También un producto con `generates_fsm_order=True` define el `fsm_service_type` a crear.
- **Mantenimiento preventivo:** cron diario sobre suscripciones (ver tabla). La orden `maintenance` finalizada (`action_finish`) reprograma según `subscription_id.maintenance_frequency`.
- **Patrullaje / ETA en vivo:** orden `patrol` toma posición del patrullero desde Traccar (`get_last_location_from_traccar`, usa `partner_id.traccar_device_id`), calcula ETA con Haversine (`_haversine_km`/`_compute_eta_minutes`) y notifica cada 3 min vía cron hasta llegada o tope de envíos.
- **Ciclo de la orden:** `action_assign` → `action_start` (check-in) → `action_arrival` (llegada al sitio) → `action_finish` (check-out, stock moves, reprogramación). `action_pause`/`action_resume` con causa; `action_request_quote` para cotización; `action_authorize_report`/`action_send_report_to_customer` para el reporte al cliente.
- **Checklist auto:** al `create`, `_populate_checklist` copia `sentinela.fsm.task.template` filtrando por `service_type` (incluye `'all'`) y por tecnología (`tech_category`, tomada de `subscription_id.service_type`).
- **Stock:** `_create_stock_moves` al finalizar descuenta los `equipment_ids` (depende de `stock`).

## Trampas conocidas
- **Server NO es git tree:** sin `rsync` previo, el `docker ... -u` actualiza con código viejo. Usar siempre skill `deploy-modulo`.
- **`data/fsm_automation_data.xml` y `fsm_patrol_data.xml` son `noupdate="1"`:** cambiar intervalos/estado de los crones por XML NO se reaplica en un upgrade; ajustar el registro en BD o forzar.
- **Traccar/SentiCar:** credenciales/URL vienen de `ir.config_parameter` (`sentinela.traccar_api_url/_user/_password`) con fallback hardcodeado `http://172.20.0.2:8082` y `admin/admin`. Requiere `partner_id.traccar_device_id` del técnico. El `try/except` traga errores silenciosamente (retorna `False`).
- **`_action_confirm` usa `hasattr(order, 'target_transfer_address_id'/'subscription_id')`:** acoplado a campos que define `sentinela_subscriptions`; si esa dependencia cambia nombres, la auto-creación rompe en silencio.
- **El cron de mantenimiento avanza `next_maintenance_date` aun si ya había orden abierta:** intencional (no regenerar a diario), pero significa que la fecha puede adelantarse sin que se haya cerrado el servicio anterior.
- **Token de rastreo:** cada orden recibe un `tracking_token` (uuid4) en `create`; los portales públicos `/rastreo/<token>` y `/SentiCar/rastreo/<token>` dependen de él (auth `public`).
- **`portal.mixin` en la orden:** hereda comportamiento de portal/acceso por token además del chatter.

## Wizards / Controllers / Tests
**Wizards (wizard/):**
| `_name` | Para qué |
|---|---|
| `sentinela.fsm.generate.order.wizard` | Crear orden manualmente (`action_create_order`); usa `FSM_SALE_SERVICE_TYPES`. |
| `sentinela.fsm.order.pause.wizard` | Pausar orden con causa/notas. |
| `sentinela.fsm.chat.send.message.wizard` | Enviar mensaje de chat al cliente. |
| `sentinela.fsm.create.route.wizard` | Generar ruta optimizada del técnico. |

**Controllers (controllers/):**
- `main.py` — extiende `web_client`: redirige a técnicos de campo a su portal (`_user_is_field_tech` / `_login_redirect`).
- `portal.py` — portal del cliente: `/my/services`, `/my/services/new`, `/my/services/submit` (alta de solicitud).
- `tech_portal.py` — portal del técnico (`/tech/dashboard`, `/tech/order/<id>` y POSTs `start`/`resume`/`arrival`/`save`/`pause`/`quote`); también un tracking público `/rastreo/<token>`.
- `tracking_portal.py` — tracking público del cliente `/SentiCar/rastreo/<token>` + endpoint JSON de datos.

**Tests:** no existen tests en el módulo.
