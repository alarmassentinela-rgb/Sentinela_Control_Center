# Runbook de despliegue a Producción — WS-2 (`sentinela_api`) → V18

> Despliegue del addon `sentinela_api` (cierre de WS-2) a producción `Sentinela_V18`.
> **No ejecutar sin ventana de mantenimiento definida por Enrique.** Validado previamente en STAGING (12/12 + datos reales).
> Cierra además un **hueco pre-existente** de `digital_sign` (portal veía todos los `sign.document`).

## 0. Pre-checks (estado al 2026-06-26)
- [x] **Respaldo DB reciente:** `DB_Sentinela_V18_2026-06-26_0800.sql.gz` (cron cada 8h). ✅
- [x] **Respaldo addons:** `ADDONS_2026-06-26_0000.tar.gz` (cron diario). ✅
- [x] **Respaldo código:** GitHub `Sentinela_Control_Center` al día (push automation). ✅
- [ ] **Respaldo manual extra justo antes** (recomendado): `bash /home/egarza/scripts/backup_pro.sh` o `pg_dump` puntual.
- [ ] **Ventana de mantenimiento** definida: ____ (fecha/hora). Impacto esperado: breve recarga de registry al `-i` (segundos). Usuarios internos: sin cambios funcionales.

## 1. Identificar contenedor de producción
```bash
ssh 192.168.3.2 'docker ps --format "{{.Names}}\t{{.Image}}" | grep -i odoo'
# Prod V18 = contenedor con dbfilter ^Sentinela_V18$ (NO odoo-lab). Confirmar antes de continuar.
```

## 2. Respaldo manual inmediato (dentro de la ventana)
```bash
ssh 192.168.3.2 'bash /home/egarza/scripts/backup_pro.sh'   # o pg_dump Sentinela_V18
```

## 3. Desplegar código (rsync — el server NO es git tree)
```bash
cd /mnt/c/Users/dell/DellCli
rsync -az --delete -e "ssh -p 2222" --exclude='__pycache__' --exclude='*.pyc' \
  sentinela_api/ 192.168.3.2:/home/egarza/odoo18-migration/addons/sentinela_api/
```

## 4. Instalar el módulo en V18  (es NUEVO en prod → `-i`)
> Puertos libres para no chocar con la instancia viva; `--stop-after-init`. SIN `--test-enable` en prod.
```bash
ssh 192.168.3.2 'docker exec <CONTENEDOR_PROD> odoo -d Sentinela_V18 -i sentinela_api \
  --stop-after-init --http-port 8169 --gevent-port 8173'
# Esperado: exit 0, "Module sentinela_api loaded", "Registry loaded".
```

## 5. Smoke tests inmediatos (post-deploy)
```bash
# 5a. Suite de seguridad sobre V18 (TransactionCase = rollback, NO deja datos):
ssh 192.168.3.2 'docker exec <CONTENEDOR_PROD> odoo -d Sentinela_V18 -u sentinela_api \
  --test-enable --test-tags /sentinela_api --stop-after-init --http-port 8169 --gevent-port 8173 \
  2>&1 | grep "failed,"'
# Esperado: "0 failed, 0 error(s) of 12 tests".
```
```python
# 5b. Endpoints base vivos (tras recargar la instancia o vía la instancia viva):
#   GET https://api.sentinela.mx/v1/config/theme  -> 200 JSON branding
#   GET /v1/me (con sesion de un usuario portal)   -> 200 perfil propio
```

## 6. Validar Portal con 1-2 clientes de prueba (datos reales, con rollback)
```bash
ssh 192.168.3.2 'docker exec -i <CONTENEDOR_PROD> odoo shell -d Sentinela_V18 \
  --http-port 8169 --gevent-port 8173' <<'PY'
# (mismo script de aislamiento usado en STAGING)
# Verificar: cliente A ve SOLO lo suyo; 0 fuga de B; sign.document aislado; admin ve totales.
env.cr.rollback()
PY
```
- [ ] Cliente A: ve solo sus servicios/facturas/eventos/documentos.
- [ ] Cliente B: 0 registros de A.
- [ ] `sign.document`: aislado (cierre del hueco pre-existente confirmado en prod).

## 7. Validar usuarios internos (sin regresión)
- [ ] Operador monitoreo, despacho FSM, cobranza, admin: acceso completo como antes.
- [ ] Crones/automatismos operan igual.

## 8. Criterio de cierre en Producción
- [ ] Pasos 4–7 ✅ → **WS-2 cerrado definitivamente en Producción.**

## 9. Plan de rollback
- **Módulo nuevo y aislado:** desinstalar `sentinela_api` (Apps → Desinstalar) — no toca datos de negocio.
  ```bash
  ssh 192.168.3.2 'docker exec <CONTENEDOR_PROD> odoo -d Sentinela_V18 --stop-after-init \
    --http-port 8169 -i base'   # o desinstalar vía UI / script de uninstall
  ```
- **Si algo grave:** restaurar `DB_Sentinela_V18_2026-06-26_0800.sql.gz` (último backup) — solo en caso extremo.
- El addon es **aditivo** (solo grupo + record rules + ACL + controllers de lectura); no migra datos.

## Riesgos
- 🔴 Mientras NO se despliegue, el hueco de `sign.document` sigue abierto en prod (cualquier usuario portal existente ve todos los documentos). El deploy lo cierra.
- 🟡 La instancia viva no sirve el módulo hasta recargar (reinicio del contenedor) — programar dentro de la ventana.
