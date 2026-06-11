# sentinela_chatwoot_bot

Bot de **primera línea de reportes** de Sentinela. Es el AgentBot de Chatwoot del
inbox **"Reportes Sentinela"** (número 8688225875): recibe los mensajes entrantes
de WhatsApp, **identifica al cliente por teléfono en Odoo**, **crea la orden FSM**
(`sentinela.fsm.order`, `repair`/Nuevo) con folio, deja una **nota interna con la
ficha del cliente** y hace **handoff a recepción** (team soporte). Reemplaza el
intake manual desde el celular.

> App standalone (NO es módulo Odoo). Vive en este repo y se versiona aquí; se
> despliega por **rsync + docker compose** (NO usa `release-modulo`/`deploy-modulo`).

## Arquitectura del flujo
```
WhatsApp 8688225875
  → EvoApi (instancia SentinelaReportes)
  → Chatwoot inbox #1 "Reportes Sentinela" (Channel::Api, cuenta #1)
  → [AgentBot] POST http://sentinela-chatwoot-bot:8090/chatwoot/agentbot
       → odoo.py  (XML-RPC 192.168.3.2:8070, api_user → Sentinela_V18)
       → crea sentinela.fsm.order + responde folio por la API de Chatwoot
       → asigna team "soporte" + abre la conversación (handoff humano)
```
- El contenedor se une a la red `chatwoot_default` y **NO publica puerto**: solo el
  rails de Chatwoot (misma red) alcanza el webhook → aislamiento por red.
- El bot responde y opera con el **access_token del AgentBot** (header
  `api_access_token`), no con el de un agente humano.

## Archivos
| Archivo | Rol |
|---|---|
| `app.py` | Webhook `POST /chatwoot/agentbot` + `GET /status`. Orquesta: guards/idempotencia → historial → **decisión del LLM** → ejecuta (reply / create_ticket / handoff). |
| `llm.py` | Cliente síncrono de OpenRouter (`chat_completion`). Mismo proveedor/modelo que OpenClaw (gemini-2.5-flash default). |
| `state.py` | SQLite (`/data/state.db`, volumen): historial conversacional por `conv_id` + flag de orden creada. El AgentBot NO puede guardar estado en Chatwoot, por eso lo lleva el bot. |
| `chatwoot.py` | Cliente de la API de Chatwoot: `send_message` (público/nota privada), `assign_team`, `toggle_status`. (El AgentBot NO puede `labels` ni `GET conversation`.) |
| `odoo.py` | Capa XML-RPC **reusada verbatim del bot OpenClaw** + `create_reconcile_fsm_order` (orden POR CONCILIAR). Lee `ODOO_*` de env. |
| `config.py` | Config por env (Chatwoot, Odoo, LLM, handoff, horario) + el **SYSTEM_PROMPT** del asistente. |
| `docker-compose.yml` | Servicio `sentinela-chatwoot-bot` en red externa `chatwoot_default` + volumen `bot_state:/data`. |
| `.env.example` | Plantilla. El `.env` real (Odoo, token AgentBot, OpenRouter) NO se versiona. |

## Lógica de decisión (app.py `_process`) — conversacional con IA
1. Ignora lo que no sea `message_created` + `message_type=incoming` del inbox configurado.
2. **Idempotencia por status:** si la conversación ya está `open`/`resolved` (handoff hecho
   o humano la tomó), el bot calla. `_handled` cubre reintentos del mismo proceso. (El status
   es lo único de idempotencia que el AgentBot puede leer Y escribir.)
3. Guarda el turno del cliente en `state` (historial).
4. **Atajo duro de handoff:** si el texto trae `asesor`/`humano`/… → handoff inmediato
   (escape a humano garantizado aunque el LLM falle).
5. Resuelve la **ficha Odoo** (`find_partner_by_phone` + `get_client_summary`) → al system prompt.
6. **El LLM decide** (system prompt + historial) y responde JSON `{action, message, summary}`:
   - `reply` → responde (saluda, pregunta, junta detalle). NO crea nada.
   - `create_ticket` (solo tras confirmación) → crea la orden FSM con `summary` (match → ligada
     a la sub si hay UNA activa; sin match → **POR CONCILIAR** con partner placeholder), responde
     el **folio** (plantilla, NO el LLM), nota interna con la ficha, handoff a soporte. Guarda el
     folio en `state` (anti-duplicado).
   - `handoff` → pasa a humano (asigna soporte + abre), sin crear orden.
   - LLM falla/parsea mal → fallback seguro: pide el detalle (no crea nada).
7. **Horario** (`OFFICE_*`): solo cambia el texto del folio; en ambos casos queda en cola de soporte.

## El cerebro: SYSTEM_PROMPT (config.py)
Saluda cálido y breve (español MX), una pregunta a la vez, junta QUÉ falla y DESDE CUÁNDO,
**no inventa folios/datos/tiempos**, ignora relleno ("hola/sí/ok"), RESUME y pide confirmación
antes de `create_ticket`, y hace `handoff` si piden humano o el tema no es reporte (ventas/cobranza).
Ajustable por env `SYSTEM_PROMPT`.

## Configuración / dependencias externas (estado vivo → memoria, no aquí)
- **Odoo:** `api_user` debe estar en el grupo `sentinela_fsm.group_fsm_dispatcher`
  (regla permisiva) para poder crear órdenes — ya aplicado para el bot OpenClaw.
- **Chatwoot:** cuenta #1 "Sentinela", inbox #1 "Reportes Sentinela", teams
  1 ventas / 2 soporte / 3 administracion. El **AgentBot** debe existir y estar
  conectado al inbox; su `outgoing_url` = `http://sentinela-chatwoot-bot:8090/chatwoot/agentbot`.

## Deploy
```bash
# 1. rsync local → server (excluye .env y caches)
rsync -avzc --delete --exclude='__pycache__' --exclude='*.pyc' --exclude='.env' \
  -e "ssh -p 2222 -i ~/.ssh/id_rsa_sentinela" \
  "/mnt/c/Users/dell/DellCli/sentinela_chatwoot_bot/" \
  "egarza@192.168.3.2:/opt/sentinela_chatwoot_bot/"
# 2. en el server (primera vez: crear .env desde .env.example)
ssh ... "cd /opt/sentinela_chatwoot_bot && sudo docker compose up -d --build"
# 3. logs
ssh ... "sudo docker logs sentinela-chatwoot-bot --tail 40"
```

## Trampas
- **Permisos del AgentBot (importante):** el token del AgentBot SOLO autoriza
  `POST messages` / `assignments` / `toggle_status`. **NO** puede `GET conversation`
  ni `POST labels` (401 "not authorized for bots"). Por eso la idempotencia es por
  `status` (no por etiqueta) y no se lee la conversación.
- **Entrega saliente Chatwoot→WhatsApp (EvoApi):** verificada para mensajes de AGENTE
  humano, pero en pruebas los salientes del bot quedaron `failed` (status 3). En logs
  de EvoApi: `ERROR [ChatwootService] Error updating Chatwoot message source ID:
  getaddrinfo EAI_AGAIN host` — EvoApi no resuelve un host "host" al confirmar el
  source_id. **Pendiente validar entrega real del bot end-to-end** (con número propio)
  antes de activar el AgentBot en producción.
- **AgentBot activable/desactivable:** la conexión al inbox es `AgentBotInbox`
  (`status: active|inactive`). Inactivo = el bot no intercepta; el inbox vuelve a
  100% humano. Reactivar = `AgentBotInbox.find_by(inbox_id:1).update!(status: :active)`.
- **Token del AgentBot:** sin `CHATWOOT_BOT_TOKEN` el bot recibe eventos pero no
  puede responder (401). Se obtiene de la fila `agent_bots` / su `access_token`.
- **Red:** si `chatwoot_default` cambia de nombre (recrear Chatwoot), actualizar
  `docker-compose.yml`. El alias `rails` del CHATWOOT_BASE_URL depende del nombre de
  servicio en el compose de Chatwoot.
- **`partner_id` es obligatorio** en `sentinela.fsm.order`: por eso el caso sin match
  usa el partner placeholder en vez de dejarlo vacío.
- **Idempotencia depende de la etiqueta** `reporte-registrado`: si se borra a mano, el
  siguiente mensaje del cliente podría generar una segunda orden.
- El bloque `import config` original de `odoo.py` se quitó (era vestigial); aquí
  `odoo.py` es autocontenido (solo env).
