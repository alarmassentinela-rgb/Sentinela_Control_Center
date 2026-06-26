# Alertas del COC Gateway → Telegram

`alert_checker.py` sondea el gateway y alerta a Telegram. Sin dependencias (stdlib).

## Reglas
- `/health` ≠ 200 → 🔴 Gateway caído.
- `/v1/providers/health` `healthy=false` → 🔴 Proveedor OTP no disponible.
- `otp_provider_up=0` → 🟠 instancia WhatsApp caída.
- `otp_send_total{result="circuit_open"}` > 0 → 🟠 circuit breaker abierto.
- `otp_send_total{result="fail"}` > 0 → 🟠 fallos de envío.

## Despliegue (cron, cada 2 min)
```bash
# env con el bot de alertas (reusar el bot interno de Sentinela)
*/2 * * * * GW_BASE_URL=http://127.0.0.1:8400 \
  TELEGRAM_BOT_TOKEN=<token> TELEGRAM_CHAT_ID=<chat> \
  /usr/bin/python3 /opt/sentinela_coc/infra/alerts/alert_checker.py >> /var/log/coc_alerts.log 2>&1
```

## Métricas y panel
- `/metrics` (texto Prometheus) → scrapear con Prometheus/Grafana del NOC si se desea panel.
- Para un panel rápido, el mismo checker puede ampliarse a más reglas (latencia alta, reuse de refresh leyendo auditoría).
