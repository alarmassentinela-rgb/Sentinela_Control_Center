# infra — Despliegue y observabilidad del COC

- **Despliegue:** `rsync` al server (192.168.3.2) + `docker compose up -d --build`. **STAGING primero**, prod solo al cumplir criterios de aceptación y pruebas de seguridad.
- **Exposición:** Cloudflare Tunnel + Nginx Proxy Manager → `api.sentinela.mx` (gateway) y `portal.sentinela.mx` (SPA).
- **Observabilidad (WS-8):** healthchecks (`/health`, `/readyz`), logging estructurado JSON con `request_id`, métricas (`/metrics`), monitoreo de uptime/alertas.
- **Secretos:** vault / variables de entorno; nunca en repo (`.env` gitignored).

> Detalle de despliegue por entorno se documenta aquí conforme avanza WS-5/WS-8.
