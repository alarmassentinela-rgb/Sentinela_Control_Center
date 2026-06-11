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
| `app.py` | Webhook `POST /chatwoot/agentbot` + `GET /status`. Toda la lógica de decisión (filtro de evento/inbox, idempotencia, handoff, intake, ficha, horario). |
| `chatwoot.py` | Cliente de la API de Chatwoot: `send_message` (público/nota privada), `add_labels`, `assign_team`, `toggle_status`, `get_conversation`. |
| `odoo.py` | Capa XML-RPC **reusada verbatim del bot OpenClaw** + `create_reconcile_fsm_order` (orden POR CONCILIAR). Lee `ODOO_*` de env. |
| `config.py` | Configuración por env (Chatwoot, Odoo, handoff, horario, etiqueta). |
| `docker-compose.yml` | Servicio `chatwoot-fsm-bot` (container `sentinela-chatwoot-bot`) en red externa `chatwoot_default`. |
| `.env.example` | Plantilla de variables. El `.env` real (con secretos) NO se versiona. |

## Lógica de decisión (app.py `_process`)
1. Ignora todo lo que no sea `message_created` + `message_type=incoming` del inbox configurado.
2. **Idempotencia por STATUS:** si la conversación ya está `open`/`resolved`, el bot
   calla (el reporte ya se levantó y se hizo handoff, o un humano la tomó). Tras el
   intake el bot SIEMPRE pasa la conversación a `open` → los mensajes siguientes ya
   no re-disparan. El status viene en el payload y es lo único de idempotencia que el
   AgentBot puede leer Y escribir (no puede GET la conversación ni poner etiquetas).
   Un set en memoria cubre reintentos del mismo proceso antes de que propague.
4. **Handoff por palabra clave** (`asesor`, `humano`, …): mensaje + asigna soporte + abre. No crea orden.
5. **Saludo escueto** ("hola" sin detalle): pide que describan el problema. No crea orden.
6. **Intake:** `find_partner_by_phone` → con match crea orden ligada (si hay UNA sub
   activa la liga); sin match crea **orden POR CONCILIAR** (partner placeholder
   `⚠ POR CONCILIAR (Reportes Web)`, con tel+texto en la descripción). Responde folio.
7. Nota interna con la **ficha Odoo** (`get_client_summary`) para recepción.
8. **Horario** (`OFFICE_*`, América/MX, L-V 9-18 por default): en horario abre+asigna
   para seguimiento inmediato; fuera de horario deja mensaje honesto y la conversación
   en el inbox para el día hábil siguiente.

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
