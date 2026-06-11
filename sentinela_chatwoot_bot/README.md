# Sentinela Chatwoot FSM Bot

Bot de reportes de primera línea: AgentBot de Chatwoot que convierte un mensaje de
WhatsApp en una **orden de servicio (FSM) en Odoo** con folio, y hace handoff a un
asesor. Detalle técnico en [CLAUDE.md](CLAUDE.md).

## Qué hace
1. El cliente escribe al WhatsApp de reportes (8688225875).
2. El bot lo identifica por teléfono en Odoo y **levanta la orden FSM** (folio `OS-…`).
3. Le confirma el folio (mensaje honesto según horario de oficina).
4. Deja la **ficha del cliente** como nota interna y pasa la conversación a **soporte**.
5. Si el cliente escribe *ASESOR* en cualquier momento → lo pasa directo a un humano.

Sin match de teléfono → la orden se crea como **POR CONCILIAR** (no se pierde el reporte).

## Operación
```bash
# Logs
sudo docker logs sentinela-chatwoot-bot --tail 40 -f

# Reiniciar (cambio de .env)
cd /opt/sentinela_chatwoot_bot && sudo docker compose restart

# Rebuild (cambio de código)
cd /opt/sentinela_chatwoot_bot && sudo docker compose up -d --build

# Health
curl -s localhost:8090/status   # solo dentro de la red de Chatwoot
```

## Primer arranque
1. `cp .env.example .env` y rellena `ODOO_PASSWORD` + `CHATWOOT_BOT_TOKEN`.
2. Crea el AgentBot en Chatwoot y conéctalo al inbox "Reportes Sentinela"
   (`outgoing_url = http://sentinela-chatwoot-bot:8090/chatwoot/agentbot`).
3. `sudo docker compose up -d --build`.
