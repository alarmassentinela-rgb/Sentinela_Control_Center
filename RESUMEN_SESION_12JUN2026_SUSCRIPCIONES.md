# Resumen de sesión — 12-jun-2026 (Suscripciones / Facturación / GPS / Permisos)

> Sesión paralela a las de red (CCR2004) y golfbookvip del mismo día. Aquí: el corazón
> de facturación (`sentinela_subscriptions`), CFDI, GPS y un fix de permisos.
> Módulos tocados: `sentinela_subscriptions` 1.3.86→**1.3.89**, `sentinela_cfdi_prodigia` 1.1.14→**1.1.15**, `sentinela_fsm` 1.7.0→**1.7.1**.

---

## 1. Auditoría MASadmin vs Odoo (cotejo de facturación periódica)
- Se cotejó el reporte de MASadmin **"REPORTE FACT PERIODICA.pdf"** (289 clientes con facturación periódica, en Descargas) contra las suscripciones de Odoo (DB `Sentinela_V18`), emparejando por **RFC real** y por **nombre normalizado**.
- Resultado: **268 cotejados (93%)**, 18 existen en Odoo sin suscripción, 3 no encontrados (faltan por dar de alta), 5 discrepancias de ciclo, 24 subs Odoo fuera del reporte (WISP/GPS/pruebas, esperado).
- Entregables enviados a Telegram (bot `@SentinelaNet_bot`): **`AUDITORIA_FACT_PERIODICA_MASADMIN_vs_ODOO_12JUN2026.pdf`** (9 pág) y **`CLIENTES_SIN_SUSCRIPCION_ODOO_12JUN2026.pdf`** (los 18, con acción sugerida por cada uno). Scripts dejados en la raíz: `audit_fact_periodica.py`, `audit_cotejo.py`, `audit_make_pdf.py`, `audit_18_pdf.py`.
- Verificado: los 18 realmente sin suscripción (ni bajo contacto hijo).

## 2. ⚠️ INCIDENTE — scheduler de crons de Odoo caído ~23h (RESUELTO)
- Al revisar el cron de facturación se descubrió que **NINGÚN cron de prod corría desde el 11-jun 19:22 UTC**. Causa: `RuntimeError: OrderedDict mutated during iteration` en `_run_cron` → los 4 hilos de cron murieron.
- **Causa raíz:** el **receiver de alarmas de LAB** (`sentinela-receiver-lab.service`) pegaba a `http://192.168.3.2:8070` (¡puerto de PROD!) con `odoo_db: Sentinela_STAGING` → cargaba el registry de STAGING dentro del proceso de producción → carrera al iterar `registries.d`.
- **Fix aplicado y verificado:** (a) reinicio del contenedor `odoo18-migration-web-1` (revivió crons); (b) repunté el receiver de lab a `:8075` (contenedor `odoo-lab`, que ya está fijado a STAGING con `--max-cron-threads=0`); (c) `list_db = True→False` en el conf compartido (blindaje); (d) `odoo-lab` quedó **declarado en `docker-compose.yml`** (antes era `docker run` manual). Backups: `config_lab.yaml.bak_12jun2026`, `odoo.conf.bak_12jun2026`, `docker-compose.yml.bak_12jun2026`.
- Verificado: 0 logins STAGING en :8070 tras el repunte, 0 crashes de cron, crons V18 corriendo.
- Detalle: memoria [[project_odoo_cron_crash_staging_12jun2026]]. **Regla: STAGING siempre por :8075, nunca :8070.**

## 3. Gating remisión/timbrado — `requiere_factura` cableado (commit 8010b0b)
- `subscriptions` **1.3.87** + `cfdi_prodigia` **1.1.15**.
- **Análisis clave:** publicar una factura **NUNCA** timbra; el timbrado es 100% manual (`action_cfdi_stamp_prodigia`). El cron solo hace create + `action_post`.
- `_billing_generate_invoice`: el `account.move` nace `cfdi_status='pending'` si `partner.requiere_factura=True`, si no `'draft'` (remisión). Mientras no tenga `cfdi_uuid` el reporte imprime REMISIÓN en ambos casos.
- `auto_invoice` (sub) ahora es **related store de `partner.requiere_factura`** (una sola fuente de verdad, readonly). ⚠️ Al cambiar a related-store hubo que forzar recompute una vez (`env.add_to_compute`) en STAGING y PROD.
- `cfdi_prodigia`: filtros "Pendientes de Timbrar"/"Timbradas"/"Remisión" + acción server **"Timbrar con Prodigia (lote)"** en la lista de facturas.
- Validado en STAGING; desplegado a PROD. **Hallazgo:** 195/390 subs tienen `requiere_factura=True` (campo ya poblado por el cliente, no había que cotejar).
- `test_mode=True` en STAGING y PROD (sandbox) → ni manualmente se timbra de verdad hasta el go-live.

## 4. Nuevo tipo de servicio "Nombre de Dominio" (commit 85983df, subscriptions 1.3.88)
- `service_type` añade `('domain','Nombre de Dominio')` (subscription + product.template selection_add).
- `_billing_generate_invoice`: domain cobra **precio fijo del periodo (qty=1, como alarma)**, no tarifa mensual × meses.
- Producto `DOMINIO` (id=2012, $1,500 anual, SAT 81112107) ajustado: is_subscription + service_type=domain + recurring=12.
- Creadas 2 subs: **SUB-0430 Pabellón Infantil** (req_factura=True → factura, próx 2027-02-01) y **SUB-0431 Consumibles Xpress** (remisión, próx 2026-09-01), ambas $1,500/año.

## 5. Arranque de facturación SILENCIOSO (freeze parcialmente levantado)
- A petición de Enrique: **cron de facturación ENCENDIDO** para generar remisiones, **sin correos** (validación interna), y **cron de suspensión apagado**.
- `auto_send_mail` apagado en TODAS las subs (las **330** que estaban en True respaldadas en `ir.config_parameter` `sentinela.autosendmail_restore_ids` para restaurar en go-live).
- **cron id=39 (Generar Pre-Facturas) = ACTIVE**, diario 07:00 UTC. id=55 (Auto-Suspender), id=56 (Recordatorios), 40, 57 siguen **OFF**.
- Corrida de validación: 9 vencidas → 9 generadas (7 remisión + 2 factura-pendiente), **0 correos** (verificado mail.mail delta=0).
- **Monitor diario:** `/home/egarza/sentinela_billing_monitor.sh` en crontab (07:30 local) corre `billing_monitor_shell.py` vía `odoo shell` (superuser; api_user lo filtran las record-rules) y manda resumen a Telegram. Probado.

## 6. GPS — flotilla KAWAC + suspensión temporal por equipo (commit d7c3b49, subscriptions 1.3.89)
- Cargados **53 equipos GPS** de KAWAC (archivo `kawac gps.xlsx`) a **SUB-0395** (KAWAC Construcciones, gps/vehículo/Smake). 46 con SIM, 7 sin. ⚠️ 3 "no facturables" en el archivo (VENDIDO, No vehiculo×2) — Enrique los revisa; el cobro multiplica por nº de equipos activos × $324.07.
- **Nueva feature:** suspensión TEMPORAL por equipo (icono ⏸ junto al bote de basura). `device_state` (active/suspended) + `action_suspend_device`/`action_reactivate_device` (cortan/restauran SIM floLIVE en modo vehículo, deshabilitan/habilitan en SentiCar). **Equipo suspendido NO se factura** (`n_dev` = solo activos). Validado en PROD (sin SIM, para no cortar SIMs reales): suspender bajó el conteo 53→52.

## 7. Permisos — por qué Enrique Garza Bedolla no entraba a Suscripciones (commit 67fc77d, fsm 1.7.1)
- **Causa:** FSM agrega `fsm_order_ids` a la suscripción; abrir una sub lee `sentinela.fsm.order` → un usuario con acceso a Suscripciones pero **sin grupo FSM** recibía `AccessError`. No era permiso de suscripciones (esos los tenía).
- **Fix puntual:** Enrique Garza Bedolla (id=7) → grupo FSM **Recepción/Despacho**. Verificado: abre OK.
- **Fix de fondo:** ACLs **read-only** sobre los modelos FSM (order/evidence/order_line/equipment/work_log/chat_message) para `group_subscription_user` (el Gestor hereda). Verificado: un usuario solo-suscripciones abre las subs y **lee** FSM pero **no escribe**. **Ya no hay que dar grupo FSM a usuarios nuevos de Suscripciones.**
- Auditoría: de 4 usuarios internos con acceso a Suscripciones, solo Enrique estaba bloqueado.
- Detalle: memoria [[reference_fsm_subscription_permiso_coupling]].

---

## Memoria actualizada esta sesión
- **Creada** `project_odoo_cron_crash_staging_12jun2026.md` (incidente cron + fix + topología odoo-lab/compose).
- **Creada** `reference_fsm_subscription_permiso_coupling.md` (gotcha permisos + fix de fondo).
- **Actualizada** `project_email_freeze_migracion.md` (gating requiere_factura, arranque silencioso, monitor diario, service_type domain).
- Punteros añadidos en `MEMORY.md`.

## Pendientes para la próxima sesión
1. **KAWAC SUB-0395:** confirmar si $324.07 es **por equipo** (cobro = ×53 ≈ $17,176/mes) o total; decidir si se quitan los 3 equipos "no facturables" (VENDIDO / No vehiculo). La sub sigue en **borrador** (no factura hasta activarla).
2. **Go-live facturación real (~1-jul):** restaurar correos (`auto_send_mail=True` a las 330 subs guardadas en `sentinela.autosendmail_restore_ids`); Prodigia `test_mode=False` + verificar CSD real (ver [[project_email_freeze_migracion]]); reactivar crons 55/56 cuando toque cobranza.
3. **3 clientes NO encontrados** en la auditoría MASadmin (SARA GUZMAN GALINDO, SERGIO COY RUIZ, SERVICIOS Y CONSTRUCCIONES SALM): dar de alta partner + suscripción.
4. **18 sin suscripción** (PDF en Telegram): revisar los 6 con contacto hijo "/PLAN" sin sub y fusionar el duplicado Blanca Esthela Lejarza.
5. Vigilar el **monitor diario** de facturación en Telegram (primera corrida automática real: cada 07:30 local).
