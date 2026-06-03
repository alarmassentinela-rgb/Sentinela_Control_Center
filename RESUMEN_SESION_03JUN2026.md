# Resumen de sesión — 3-jun-2026

Día grande: **se desconectó Argus** (cutover completo a Odoo) + varias mejoras de UX en suscripciones + **se construyó la Fase 2** (recolector de consumo + TimescaleDB).

---

## 1. CUTOVER — Argus desconectado ✅
1. **Validación suspendidos router↔Odoo:** 7=7 consistentes. Resueltos: cta0069 (SUB-0291 AUTOTRANSPORTES CAREL) confirmado ACTIVO; cta0011 (SUB-0375 IGNACIO CARREON, baja) suspendido en router para cuadrar.
2. **Respaldo del router:** `pre_cutover_argus_03jun2026.backup` (1.75MB) + `.rsc` (110 cuentas) — en router y PC.
3. **`sync_active=True`** permanente en CCRsentinela (cron auto-suspensión verificado: 0 facturas vencidas → no corta a nadie). Probado cta0040 con sync ON.
4. **Argus DESCONECTADO** (desactivado, NO borrado): interfaz OVPN `argusblack` + 8 schedulers de cliente → disabled. **Clientes 101→101, SIN CAÍDAS** (auth local). Rollback: `ROLLBACK_ARGUS_03JUN2026.py`.
5. **Validado en vivo:** suspendí cta0193 (OMAR FLORES, SUB-0341) desde Odoo → el router lo mandó solo a walled-garden (perfil suspendido + IP en lista bloqueada por firewall). El cutover funciona en producción.

**Estado: Odoo es el único jefe del CCRsentinela. Argus apagado EN OBSERVACIÓN** (no cancelar el servicio aún).

## 2. Suscripciones — mejoras de UX (releases)
- **v18.0.1.3.65** — fix: al cambiar el Plan, la Tarifa Mensual SIEMPRE toma el precio del nuevo plan (antes solo si estaba vacía).
- **v18.0.1.3.66** — pestaña **🔧 Diagnóstico** (solo internet): agrupa Ping/Verificar Conexión/Señal + panel señal + gráfica. "Solicitar Credenciales PPPoE" se queda en Conectividad.
- **v18.0.1.3.67/68** — layout Diagnóstico lado-a-lado (señal izq · tráfico der) + **estado de conexión automático** (cron `_cron_refresh_antenna_signal` cada 15 min: online/IP de todos + señal SSH de antenas en línea, lote 25, commits incrementales). Botón "📡 Actualizar Señal".
- **v18.0.1.3.69** — estado **🟢 CONECTADA / 🔴 DESCONECTADA** debajo de "Conexión revisada"; **recuadro de resultado de Ping** debajo de la señal; quitado botón "Ver Tráfico" (la gráfica ya es automática).

## 3. Vigilante — Fase 2: Consumo + TimescaleDB ✅
Decisión: el consumo y el portal cliente van **FUERA de Odoo**, en el vigilante (un sistema, 2 interfaces: operador interno + portal cliente). Diseño: `sentinela_netwatch/DISEÑO_FASE2_CONSUMO.md`.
- **Contenedor `sentinela_timescaledb`** (puerto host 5435) + **colector `collector_traffic.py`** (hilo en el vigilante, cada 10 min).
- Lee `/interface <pppoe-cta>` (tx=descarga, rx=subida), calcula delta (maneja reset), guarda en hypertable `traffic`. Espeja `clients` desde Odoo. Agregados diario/mensual + retención 90 días.
- **Verificado:** datos reales con nombre de cliente fluyendo a TimescaleDB.

---

## PENDIENTE — mañana
1. **Vista de consumo en el dashboard operador** (gráfica por cliente / por mes) — siguiente paso de Fase 2.
2. **Fase 3 — Portal cliente** (`portal.sentinela.mx`, login OTP WhatsApp, cada cliente ve solo lo suyo).
3. **Argus en observación**: vigilar unos días que Odoo maneje todo bien; luego cancelar servicio Argus + (opcional) renombrar perfiles a Plan_5mb..30mb (router+Odoo, probado que no rompe) + limpiar schedulers ISP-failover de Argus (el PCC nuevo ya hace failover).
4. **cta0193** y demás: seguir operando suspensiones/altas desde Odoo y verificar.

## Referencias en memoria
- `reference_argus_arquitectura.md` — cómo funciona Argus (OVPN, PCQ, schedulers, cómo desconectarlo).
- `project_migracion_wisp_argus_a_odoo.md` — plan completo + estado del cutover.
- `project_netwatch_vigilante.md` — el vigilante (Fase 0) + Fase 2 (consumo/TimescaleDB).
- `ROLLBACK_ARGUS_03JUN2026.py` — reactiva Argus si hiciera falta.

---

# Sesión tarde — Módulo Gestión de Servicios (FSM) — reemplazo de 2Workers

Auditoría completa del módulo `sentinela_fsm` + cierre de los 7 gaps detectados + flujo de tickets recepción→coordinador→técnico + **intake desde WhatsApp**. Todo en producción (Sentinela_V18), validado primero en STAGING.

## Releases del día (FSM)
| Versión | Qué |
|---------|-----|
| **fsm 18.0.1.1.0** | **Mantenimiento preventivo funcional** (gaps 1-3): campos `maintenance_frequency`/`next_maintenance_date`/`last_maintenance_date` en sentinela.subscription (se usaban sin existir → rompían cron y action_finish); registrado el `ir.cron` que nunca se disparaba; nuevo tipo de orden "Mantenimiento Preventivo" + se aclaró "Reparación/Falla". El cron crea órdenes `maintenance` y avanza la fecha. |
| **fsm 18.0.1.2.0** | **Flujo explícito Venta→Orden** (gaps 4-5): bandera `generates_fsm_order` + `fsm_service_type` en el producto (opt-in, ya no adivina por nombre); `sale_order_id` en la orden + smart button con contador en la venta; botón "Generar Orden de Servicio" + wizard manual. Pre-marcados 4 productos de campo (11679/11680 install, 1963 transfer, 1961 repair). |
| **fsm 18.0.1.2.1** + **monitoring 18.0.1.6.0** | **Traccar fuera del código** (gap 6): credenciales API a parámetros del sistema (`sentinela.traccar_api_url/_user/_password`) con fallback; bloque "Radar SentiCar / Traccar" en Ajustes de Central. **Mapeo patrullero↔device** (gap 7): campos GPS en form de res.users + vista/acción/menú "Patrulleros (GPS)". |
| **monitoring 18.0.1.7.0** | **Botón "🚓 Enviar Patrullero"** en el evento de alarma → wizard `sentinela.patrol.dispatch.wizard`: el operador elige patrullero → crea orden de patrullaje asignada con info del evento + coords + notifica al patrullero. El cliente recibe "va en camino" + link SentiCar + nombre cuando el patrullero confirma "Ya salí" en su app (action_start, ya existía). |
| **fsm 18.0.1.3.0** | **Flujo reporte de falla (recepción→coordinador→técnico)**: recepción puede fijar tipo de falla + prioridad al crear (antes readonly); `action_assign` valida técnico+fecha; menú "Nuevo Reporte" (intake 1 clic); badges de mantenimiento/traslado/retiro/patrullaje en el portal del técnico. El técnico ve sus pendientes con día/hora en `/tech/dashboard` y "Mis Órdenes" (ya existía). |
| **fsm 18.0.1.3.1** | **Grupo "Recepción / Despacho"** (group_fsm_dispatcher, regla permisiva): el grupo Técnico solo ve órdenes propias, lo que bloqueaba a recepción y al bot al crear tickets de otros. Recepción y el api_user del bot van aquí; Manager implica ambos. |

## Intake desde WhatsApp (Opción A LISTA) — bot OpenClaw
El bot vive en server `/home/egarza/openclaw/` (no está en git). Backups: `{bot,odoo}.py.bak_03jun`.
- **Bug arreglado:** `odoo.py create_fsm_order` creaba un `project.task` falso → ahora crea `sentinela.fsm.order` real (repair, 'new', liga suscripción única) y devuelve folio.
- **`bot.py`:** comando **SOPORTE / FALLA / REPORTE `<descripción>`** → identifica al cliente por teléfono, crea el ticket, confirma folio al cliente, avisa al owner. Número no identificado → avisa al owner.
- **Permiso:** `api_user` (id=10) agregado a `group_fsm_dispatcher` en V18 y STAGING. Create verificado por XML-RPC en ambas BDs.
- Flujo completo: cliente reporta por WhatsApp → ticket 'Nuevo' → coordinador agenda → al técnico le aparece en su app.

## PENDIENTE FSM — mañana
1. **Intake WhatsApp Opción B/C**: que la IA detecte la falla en charla normal ("mi internet no sirve") y sugiera/cree el ticket (nudge "escribe SOPORTE..."). El cliente eligió C empezando por A (ya hecho A).
2. **Agregar usuarios humanos de recepción** al grupo "Recepción / Despacho" (no al de Técnico).
3. Configurar en *Ajustes de Central* la API Traccar real y mapear patrulleros↔device en "Patrulleros (GPS)".
4. (Opcional) Respaldar el bot OpenClaw al repo (hoy es server-only, riesgo de pérdida como pasó con cfdi_prodigia).
5. Probar el ciclo end-to-end en UI (venta→orden; reporte→agenda→técnico; despacho patrulla).

## Referencias en memoria (FSM)
- `project_fsm_gestion_servicios.md` — estado del módulo, flujos, grupos, roadmap (gaps 1-7 cerrados).
- `project_openclaw_bot.md` — bot WhatsApp + intake de tickets (opción A).
