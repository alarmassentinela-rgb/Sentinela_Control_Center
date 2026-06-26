# Checklist de Producción — Portal COC RC1

> Verificaciones previas y durante la ventana de despliegue. Todos en ✅ antes de declarar éxito.

## A. Pre-ventana
- [ ] RC en verde (suites + e2e + pentest + perf) — ver `ACCEPTANCE_CHECKLIST_COC_RC1.md`.
- [ ] Instancia WhatsApp `SentinelaWA` **conectada** (`/v1/providers/health` → healthy) y smoke real OTP OK.
- [ ] Respaldo DB reciente + respaldo manual extra ejecutado.
- [ ] Código en GitHub al día.
- [ ] Secretos en vault/env (no en repo): JWT, secreto compartido, EvoApi key, DB gateway.
- [ ] Dominios/DNS listos: `api.sentinela.mx` (gateway). `/coc/internal/*` restringido a LAN.
- [ ] Ventana de mantenimiento comunicada.

## B. Durante el despliegue
- [ ] `sentinela_api -i` en V18: exit 0, registry OK.
- [ ] Reinicio del contenedor prod (sirve rutas nuevas).
- [ ] Gateway `docker compose up -d --build`: `/health` 200.
- [ ] `sentinela_api.gateway_shared_secret` sembrado y coincide con `COC_COC_SHARED_SECRET`.

## C. Post-deploy (smoke)
- [ ] Seguridad: cliente A no ve datos de B (record rules) — pruebas negativas.
- [ ] No-regresión interna: admin/operador/cobranza ven todo como antes.
- [ ] Auth: OTP real a número de prueba → login → `/v1/me` con datos propios.
- [ ] Sesiones: cerrar individual/global funciona; access revocable.
- [ ] EvoApi: `/v1/providers/health` healthy; métricas en `/metrics`.

## D. Observabilidad
- [ ] Logs estructurados con `request_id` fluyendo.
- [ ] `/metrics` accesible para el scrapeo/monitoreo.
- [ ] Alertas configuradas (proveedor down, error-rate, OTP fail spike) — ver `OBSERVABILITY_COC.md`.

## E. Cierre
- [ ] Smoke en verde → declarar éxito. Si no → rollback (runbook §6).
- [ ] Registrar resultado en `docs/releases/Sprint-03.md` y marcar WS-2/WS-5 cerrados en Producción.
