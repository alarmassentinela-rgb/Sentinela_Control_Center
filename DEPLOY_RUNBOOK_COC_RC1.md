# Runbook de despliegue — Portal COC RC1 (WS-2 + WS-5 + EvoApi)

> **Ventana única** para Producción. No ejecutar sin: RC en verde + instancia WhatsApp conectada + smoke real OTP OK + Checklist de aceptación aprobado.
> Sustituye/extiende a `DEPLOY_V18_WS2_RUNBOOK.md` (que cubría solo WS-2).

## 0. Pre-requisitos
- [ ] `ACCEPTANCE_CHECKLIST_COC_RC1.md` aprobado.
- [ ] Respaldos: DB (cron 8h) + addons (diario) + código en GitHub. Respaldo manual extra justo antes.
- [ ] Secretos definidos (vault/env), NO en repo: `COC_JWT_SECRET`, `COC_COC_SHARED_SECRET` (= `sentinela_api.gateway_shared_secret` en Odoo), `COC_WA_API_KEY`, DB del gateway.
- [ ] Ventana de mantenimiento acordada.

## 1. Componente A — Odoo addon `sentinela_api` (V18)
```bash
# rsync (server NO es git tree)
rsync -az --delete -e "ssh -p 2222" --exclude='__pycache__' --exclude='*.pyc' \
  sentinela_api/ 192.168.3.2:/home/egarza/odoo18-migration/addons/sentinela_api/
# instalar en prod (modulo NUEVO) con puertos libres, --stop-after-init
ssh 192.168.3.2 'docker exec <CONTENEDOR_PROD_V18> odoo -d Sentinela_V18 -i sentinela_api \
  --stop-after-init --http-port 8169 --gevent-port 8173'
# sembrar el secreto compartido en Odoo (si no existe)
#   ir.config_parameter sentinela_api.gateway_shared_secret = <secreto>
```
- Esperado: exit 0, "Module sentinela_api loaded", "Registry loaded".
- Reiniciar el contenedor prod para servir las rutas `/coc/internal/*` y `/v1/*`.

## 2. Componente B — Gateway (FastAPI, Docker)
```bash
rsync -az -e "ssh -p 2222" --exclude='__pycache__' --exclude='.env' \
  sentinela_coc/ 192.168.3.2:/opt/sentinela_coc/
# .env de PRODUCCION (fuera de git) con secretos + COC_OTP_PROVIDER=evoapi + COC_ODOO_BASE_URL
ssh 192.168.3.2 'cd /opt/sentinela_coc/gateway && docker compose up -d --build'
```
- Exposición: Cloudflare Tunnel + NPM → `api.sentinela.mx` (gateway). Odoo `/coc/internal/*` **solo LAN** (no exponer a internet).

## 3. Componente C — SPA (cuando exista; RC1 no la incluye)
- `portal.sentinela.mx` (Next.js). N/A en RC1.

## 4. Orden recomendado
1. Addon `sentinela_api` (`-i` en V18) + reinicio prod.
2. Verificar record rules (smoke seguridad, ver `SMOKE_TESTS_COC.md`).
3. Gateway up + `/health` + `/v1/providers/health` (EvoApi open).
4. Smoke de autenticación (OTP real a número de prueba).
5. Verificación de no-regresión interna.

## 5. Smoke post-deploy
Ver `SMOKE_TESTS_COC.md` (health, OTP real, /v1/me scoped, métricas).

## 6. PLAN DE ROLLBACK
| Componente | Rollback | Datos |
|---|---|---|
| `sentinela_api` | Desinstalar módulo (Apps → Desinstalar) — es aditivo, no migra datos | sin pérdida |
| Record rules/ACL | revertir commit + `-u`; o deshabilitar `ir.rule` del grupo portal | sin pérdida |
| Gateway | `docker compose` a imagen/tag anterior (stateless) | `portal_identity` con respaldo previo |
| Caso extremo | restaurar `DB_Sentinela_V18_<fecha>.sql.gz` | último backup |
- El addon **no cambia** comportamiento de usuarios internos (validado). Rollback de bajo riesgo.

## 7. Criterio de éxito del despliegue
- Smoke post-deploy en verde + no-regresión interna + observabilidad activa (`/metrics`, logs, alertas). Si algo falla → rollback del componente afectado.
