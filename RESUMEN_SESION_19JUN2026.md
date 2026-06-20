# Resumen de Sesión — 19 de junio de 2026

Sesión enfocada en un incidente de cobranza/red (SUB-0325) y una tanda de mejoras al
módulo FSM (Gestión de Servicios). 7 releases desplegados y verificados en V18.

---

## 1. WISP / Suscripciones — Incidente SUB-0325 "pagó pero sin servicio"

**Cliente:** Gloria Delia Belmares Farías, cta0170, CCR Matamoros (192.168.10.50).

**Síntoma:** suspendida por falta de pago; se aplicó el pago pero el cliente seguía sin internet.

**Diagnóstico:** en Odoo todo estaba correcto — factura INV/2026/00075 **pagada**, pago HSBC
conciliado, y la **reactivación automática por pago sí disparó** (technical_state=active a las
16:30 hora local Matamoros = 21:30 UTC). El problema estaba en el CCR:
- La reactivación cambió el perfil del *secret* PPPoE al plan correcto…
- …pero **NO cortó la sesión PPPoE activa**. En MikroTik el perfil solo se aplica al conectar,
  así que la cliente seguía corriendo sobre la sesión vieja (~15:48 local) con el perfil
  **walled-garden**, y su IP `172.16.10.229` seguía en el address-list `argusblack_servicio_suspendido`.
- La "validación de navegación" de las 16:36 fue **falso positivo** (contó las respuestas del
  propio walled-garden como tráfico real).

**Fix en vivo:** corte de la sesión PPPoE + retiro de la IP del address-list → reconectó con
`argusblack_plan_841_1797`, fuera del walled-garden. **Verificado:** sesión nueva, navegando.

**Nota de zona horaria:** Odoo guarda en UTC; la consola muestra UTC. Local = America/Matamoros
(CDT, UTC−5 en junio). Restar 5 h a los timestamps de chatter leídos por shell.

### 1.1 Fix de código — `sentinela_subscriptions v18.0.1.4.2` (commit 0faee93)
`action_provision_mikrotik_enable` ahora es simétrico al disable: **corta la sesión activa** y
**limpia el address-list por dirección** (las entradas del walled-garden son dinámicas y sin
comment, antes solo se buscaba por comment → nunca se borraban). Evita que cualquier cliente
reactivado por pago quede atorado.

**Barrido en los 3 CCR reales** (Matamoros 93 subs / Monclova 4 / Balanceador 0): **0 atorados**
aparte de Gloria. Monclova tiene `sync_active=off` (el módulo no lo provisiona).

### 1.2 Fix botón Validar Navegación — `sentinela_subscriptions v18.0.1.4.3` (commit 24935f9)
El botón leía el perfil del *secret* pero no el bloqueo **real**. Ahora, antes del conntrack,
verifica si la IP está en el address-list `argusblack_servicio_suspendido` y devuelve
🔴 SUSPENDIDO sin importar el perfil. Cierra el falso 🟢. 100% lectura. Probado en vivo (Gloria
da 🟢 NAVEGANDO correcto).

---

## 2. FSM (Gestión de Servicios) — 5 releases

### 2.1 `v18.0.1.9.0` (commit 95b184c) — Orden hereda datos de la suscripción
Nuevo `@api.onchange('subscription_id')` en `sentinela.fsm.order`: al crear la orden desde el
botón "Órdenes Técnicas" de la sub (pasa `default_subscription_id`) o al elegir la sub a mano,
rellena cliente, dirección de servicio, coordenadas, cuenta de monitoreo, usuario PPPoE y una
descripción base. Solo rellena lo vacío. No toca service_type. Probado en SUB-0361.

### 2.2 `v18.0.1.10.0` (commit c217181) — Dos ejes: trabajo + tecnología
- **service_type** (tipo de trabajo) ampliado: + Revisión/Diagnóstico, Configuración,
  Reconexión en Sitio, Garantía; "Traslado" → "Traslado / Reubicación".
- **service_category** (CAMPO NUEVO, Sistema/Tecnología): internet, alarma, cctv, gps, solar,
  control de acceso, cercas eléctricas, detección de incendio, telefonía, otro.
  - Autollenado desde la sub (internet/alarm/gps) y editable a mano para órdenes **sin contrato**
    o tecnologías que la sub no maneja (CCTV, paneles, alarma sin monitoreo).
  - Visible en: form, lista, buscador/agrupar (backend), portal del técnico (lista + detalle) y
    reporte al cliente.
  - `_populate_checklist` usa service_category como tecnología cuando no hay suscripción.

  **Decisión de diseño:** se rechazó meter combinaciones ("Mantenimiento de CCTV") en un solo
  dropdown (estallido combinatorio); dos ejes separados es más limpio y filtrable. Motivado por
  que Sentinela levanta órdenes a clientes sin contrato y vende CCTV/paneles/alarma-sin-monitoreo.

### 2.3 `v18.0.1.10.1` (commit 43b295a) — Plantillas de checklist CCTV + Solar
Nuevo `data/fsm_checklist_templates.xml` (noupdate): 17 tareas CCTV (10 instalación + 7
mantenimiento) y 15 solar (8 + 7). `tech_category` de la plantilla ampliado a
solar/access/fence/fire/phone (paridad con service_category).

### 2.4 `v18.0.1.10.2` (commit 03cb8ac) — Reclasificación de plantillas mal marcadas
Las 24 plantillas existentes estaban en `tech_category='all'` pero por nombre eran de
internet/alarma/GPS → se colaban en cualquier orden (una de CCTV mostraba "corte de motor",
"botones de pánico"). Reclasificadas 15 a su tecnología real:
- internet:7, alarm:3, gps:3, cctv:19, solar:15, all:9 (genéricas + patrullaje).
- Las 4 del módulo por xml_id (corregidas también en XML fuente); las 11 manuales por nombre.
- Como están con `noupdate="1"`, un `-u` no las corrige → **actualizadas en vivo en STAGING + PROD**.
- **Verificado:** orden CCTV ahora trae 14 tareas, 0 de otra tecnología.

### 2.5 `v18.0.1.10.3` (commit 62df10e) — Dirección de entrega en ventas
`partner_shipping_id` tenía domain vacío y mostraba todo el catálogo de contactos. Se le puso
`domain="[('id','child_of',partner_id)]"` en la vista de venta heredada por FSM → solo el cliente
seleccionado y sus direcciones. Verificado en el arch combinado de prod.

---

## Estado de despliegue
Todo en producción **V18** y verificado:
- `sentinela_subscriptions` → **18.0.1.4.3**
- `sentinela_fsm` → **18.0.1.10.3**

Web reiniciado donde hubo cambios de campos/Python. Tags de respaldo en GitHub por cada release.

---

## Pendientes para mañana
1. **Dirección de Factura** (`partner_invoice_id`) tiene el mismo defecto que la de entrega
   (abre todo el catálogo). ¿Aplicar el mismo filtro `child_of partner_id`? (1 línea).
2. **Filtro `child_of partner_id`**: funciona cuando el cliente de la venta es la empresa/registro
   principal; si se pone un contacto hijo como cliente, mostraría solo lo bajo ese contacto.
   Vigilar si estorba en la práctica.
3. **Plantillas manuales (11)**: son datos vivos sin respaldo en XML; si se reinstala el módulo
   desde cero no se recrean. Evaluar versionarlas (con cuidado de no duplicar).
4. **Teléfono en orden FSM**: es related de `partner_id.phone`; si el número está en *Móvil* sale
   vacío. ¿Hacer fallback a mobile?
5. (Monitoring, heredados) ¿quitar sub-filtro "Activos" de Tráfico?; SMS al cliente (falta gateway).

---
---

# Sesión 2 (tarde-noche) — Agentes IA (Telegram + WhatsApp/Chatwoot)

Segunda sesión del día, enfocada en **agentes de IA**. Nada del módulo FSM; trabajo sobre
apps standalone (server-only, fuera del árbol de release del módulo).

## Mantenimiento WSL
- `apt update && upgrade` en el Ubuntu de la PC (45 paquetes, 0 pendientes, sin reinicio).
- Password sudo del WSL (`egarza`/`sentinela`) documentado en el índice de credenciales (§10b).

## Revisión de auto-suspensión (preventivo)
- Replicada la lógica del cron `_cron_auto_suspend_overdue` contra prod (solo lectura): **17
  suscripciones** se suspenderían al reactivar el cron, adeudo total **$8,578**. PDF a Telegram.
- ⚠️ **`api_user` está ciego a la contabilidad** (record rules) → reportes de cobranza vía esa
  credencial salen en CERO falso. Hay que usar admin (egarza uid=2) para ver `account.move`.
- Aclarado: **varias subs por cliente es NORMAL** (alarma+internet, casa+oficina, sucursales), NO
  duplicado. Memoria [[multi-sub-por-cliente-normal]].

## SentiAI — nuevo agente IA en Telegram (bot propio @SentinelaAsistente_bot)
- App nueva `/home/egarza/sentinela_tg_agent/agent.py` (long-polling, OpenRouter→`claude-sonnet-4.6`).
  **Solo responde al chat de Enrique** (7965190381); guardrail por chat_id.
- Bot **propio dedicado** (no choca con crones de Odoo que sondean los otros bots de Telegram).
- **Lectura** Odoo (clientes, suscripciones, facturas vencidas) + **escritura con CONFIRMACIÓN por
  "SÍ"**: dar prórroga (`apply_extension`) y aplicar pago (`account.payment.register`). El LLM solo
  *propone*; la ejecución la dispara código determinista al recibir "SÍ" (no puede auto-confirmarse).
- Desplegado como **systemd en el server** (`sentinela-tg-agent.service`, enabled, Restart=always),
  migrado desde la PC. Self-test OK (OpenRouter 200 + Odoo uid 2). Mecánica de pago validada en prod
  sin postear (wizard transient). 2 manuales PDF (uno con logo) a Telegram. Memoria [[agente-ia-telegram-sentiai]].

## Bot de Reportes WhatsApp (Chatwoot AgentBot, 8688225875) — go-live + ruteo
- **AgentBot REACTIVADO** (`AgentBotInbox` inbox 1 → `status=active`) tras pre-flight (webhooks
  chatwoot↔evoapi correctos, instancia `open`). El "no contestó" en la prueba era por diseño: la
  conversación estaba `open` → el bot calla (idempotencia por status); se reabre a `pending` para probar.
- **Horarios de atención humana** (app.py/config.py): `OFFICE_SCHEDULE` por día (**L-V 9-18, Sáb 9-13,
  Dom cerrado**) + `_next_office_open()`. **Bug corregido: TZ → `America/Matamoros`** (lada 868 sigue DST
  de EE.UU.; el `.env` tenía `America/Mexico_City` → el bot se creía abierto 1h de más). Handoff y folio
  ahora honestos según horario; horario inyectado al system prompt.
- **Handoff ruteado por tema + notificaciones:** el LLM clasifica `topic`; `config.ROUTING` asigna
  **equipo + agente** y Chatwoot notifica al assignee (email+push, ya activados para agentes 1/2/3):
  **cobranza/facturación→Irma, ventas→E.G.Bedolla, soporte→equipo soporte/Enrique.** `assign_agent`
  añadido a chatwoot.py (probado: el AgentBot SÍ puede asignar assignee). Manual PDF a Telegram.
- Desplegado por rsync + `docker compose up -d --build`. **Sin validar end-to-end con cliente** (regla
  dura: NO probar contra clientes reales; Enrique probaría desde su cel). Cambios de código del bot
  (`app.py/config.py/chatwoot.py/CLAUDE.md`) versionados en este commit; **el `.env` del server NO**
  (TZ/OFFICE/ROUTING quedaron también ahí, backup `.env.bak_tz_*`).

## Pendientes sesión 2
1. **Probar end-to-end** el bot de reportes desde el cel de Enrique: cobranza→Irma, ventas→EGB,
   soporte→folio. (Conversación #14 quedó en `pending` lista.)
2. **App Chatwoot** instalada por cada agente (Irma, EGB, Enrique) para que llegue el push; el email ya jala.
3. **Mirna Barbosa** (recepción, central@) tiene la cuenta Chatwoot **sin confirmar** — activarla si entra a soporte.
4. Cuando soporte tenga >1 miembro → auto-assignment round-robin.
5. SentiAI: ¿más herramientas (crear orden FSM, avisos)? ¿usuario Odoo dedicado "Agente IA" para auditoría?
6. Trampa viva: `SERVER_URL=192.168.3.2:8080` en EvoApi deja armado el webhook (no re-correr `/chatwoot/set`).
