# RUNBOOK — Deploy a producción de GolfBookVIP Fases 1–4A

Server: `192.168.3.2` (ssh -p 2222 -i ~/.ssh/id_rsa_sentinela egarza@…), prod en `/opt/golfbookvip`.
Rama a desplegar: `feat/golfbookvip-fase4a-freetier` (acumula 1→2A→2B→3→4A + rescate balances.py).

## Pre-flight (YA HECHO)
- ✅ Backup BD: `/opt/golfbookvip/backup_predeploy_20260701_192834.sql.gz`.
- ✅ Sin bloqueadores: 0 invoices con stripe_invoice_id duplicado; `alembic_version` no existe;
  `processed_stripe_events` no existe; 6 planes ya sembrados; 250G disco libre.
- ✅ Drift reconciliado: prod corría `balances.py` +150 líneas (feature breakdown) NO commiteada →
  rescatada al repo (commit 126db22). Ahora repo==prod para ese archivo.
- ✅ Único drift de config: prod `docker-compose.yml` = base + bind-mounts `./frontend/.next` y
  `./frontend/public` → NO se toca el compose en el deploy.

## ⚠️ Impacto a usuarios
El cambio de auth (Fase 2B: token en memoria + cookie de refresh) **invalida las sesiones actuales**:
los ~36 usuarios con token en localStorage quedarán deslogueados y deberán **re-loguearse una vez**.
Elegir ventana de bajo tráfico. No hay pérdida de datos.

## Ejecución (en la ventana)

### 0. Snapshot de código para rollback
```
ssh … 'cd /opt/golfbookvip && tar czf /opt/golfbookvip/rollback_code_$(date +%Y%m%d_%H%M%S).tgz app frontend/src alembic requirements.txt'
```

### 1. rsync quirúrgico local → prod (SIN --delete; preserva strays, compose, .env, creds)
```
rsync -az -e "ssh -p 2222 -i ~/.ssh/id_rsa_sentinela" \
  --exclude='frontend/node_modules' --exclude='frontend/.next' --exclude='.git' \
  --exclude='__pycache__' --exclude='*.pyc' --exclude='venv' \
  --exclude='docker-compose.yml' --exclude='.env' --exclude='firebase-credentials.json' \
  --exclude='*.sql.gz' --exclude='*.tgz' --exclude='_baseline_source' \
  "proyecto golfbookvip/"  egarza@192.168.3.2:/opt/golfbookvip/
```
(balances.py es idéntico → no-op. Trae: alembic/ nuevo, app/api/v1/billing.py, services/plans.py,
accounts.py, models actualizados, frontend/src actualizado, requirements.txt con slowapi.)

### 2. Añadir variables de cookie al `.env` de prod
```
ssh … 'cat >> /opt/golfbookvip/.env <<EOF

# Fase 2B — auth por cookie httpOnly
COOKIE_SECURE=true
COOKIE_SAMESITE=lax
COOKIE_DOMAIN=.golfbookvip.com
EOF'
```
(Opcional: bajar `ACCESS_TOKEN_EXPIRE_MINUTES` a 30 en `.env` para aprovechar el silent-refresh;
si se deja el valor actual, el sistema funciona igual con access token más largo.)

### 3. Rebuild de imágenes (nueva dep slowapi) + CUTOVER de Alembic
ORDEN CRÍTICO — las 43 tablas YA existen, así que primero `stamp 0001` (marca sin ejecutar DDL),
luego `upgrade head` (aplica solo 0002 idempotente + 0003):
```
ssh … 'cd /opt/golfbookvip && \
  docker compose build api migrate && \
  docker compose run --rm migrate alembic stamp 0001_baseline && \
  docker compose run --rm migrate alembic upgrade head'
```
Esperado: `alembic_version = 0003_stripe_idempotency`, `processed_stripe_events` creada,
`uq_invoices_stripe_invoice_id` creada. (0002 no duplica planes por ON CONFLICT.)

### 4. Rebuild del frontend (.next bind-mount) + levantar todo
```
ssh … 'cd /opt/golfbookvip && \
  docker run --rm -v /opt/golfbookvip/frontend:/app -w /app \
    -e NEXT_TELEMETRY_DISABLED=1 -e NEXT_PUBLIC_API_URL=https://api.golfbookvip.com \
    node:20-alpine sh -c "npm install --legacy-peer-deps && npm run build" && \
  docker compose up -d --build'
```
(El `up` reinicia api/frontend con el código nuevo; el servicio migrate correrá `upgrade head` = no-op
porque ya está en 0003.)

### 5. Verificación post-deploy
```
ssh … 'curl -sf http://localhost:8100/health; \
  docker exec golfbookvip_db psql -U golfuser -d golfbookvip -tA -c "SELECT version_num FROM alembic_version;"; \
  curl -s http://localhost:8100/api/v1/billing/plans | head -c 300'
```
+ prueba manual en navegador (https://golfbookvip.com): login → dashboard carga → logout. Verificar
Set-Cookie `gbv_refresh` httpOnly, y que el scoring en vivo (WS) conecta.

## Rollback
- **Código:** `tar xzf rollback_code_<ts>.tgz -C /opt/golfbookvip && docker compose up -d --build`.
- **BD (migración es aditiva):** `docker compose run --rm migrate alembic downgrade 0002_seed_plans`
  (quita processed_stripe_events + unique). Para revertir del todo: restaurar el backup
  `backup_predeploy_*.sql.gz`.
- **Env:** quitar las 3 líneas COOKIE_ del `.env`.
- **Sesiones:** los usuarios re-loguean; nada que revertir.

## Post-deploy
- Abrir tarea para desplegar balances.py→Decimal (Fase 3B) y Fase 4B (Stripe checkout).
- Actualizar el `VERSION` de prod (estaba stale en 1.15).
