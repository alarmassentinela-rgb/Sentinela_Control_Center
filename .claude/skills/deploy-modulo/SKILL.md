---
name: deploy-modulo
description: >-
  Despliega un módulo sentinela_* (o golfbookvip / aleasystem.io) al servidor
  de producción 192.168.3.2. Úsalo cuando se editó código de un addon y hay que
  aplicarlo en el server. Encadena rsync (local→server) → docker -u en STAGING
  (`Sentinela_STAGING`) → docker -u en PROD (`Sentinela_V18`) → reinicio del
  contenedor web → verificación. El server NO es git working tree: sin rsync,
  el `-u` corre código viejo; sin reinicio, el worker vivo corre el Python viejo.
  Para crear el commit/tag/push antes de desplegar, usa primero la skill release-modulo.
---

# Deploy de un módulo a producción

DellCli (local) y el server tienen **copias separadas** del código. No comparten
filesystem ni git. El cambio NO existe en producción hasta que se hace `rsync`.

## Coordenadas fijas

| Cosa | Valor |
|---|---|
| Local | `/mnt/c/Users/dell/DellCli/<modulo>/` |
| Server addons | `egarza@192.168.3.2:/home/egarza/odoo18-migration/addons/<modulo>/` |
| SSH | `ssh egarza@192.168.3.2` (puerto 2222 + llave ya en `~/.ssh/config`) |
| Container web PROD | `odoo18-migration-web-1` (sirve `Sentinela_V18`, puerto host :8070) |
| Container web LAB | `odoo-lab` (sirve `Sentinela_STAGING` por navegador `http://192.168.3.2:8075`) |
| Container db | `odoo18-migration-db-1` (postgres; tiene AMBAS DBs: `Sentinela_V18` y `Sentinela_STAGING`) |
| DB staging | `Sentinela_STAGING` (validar SIEMPRE primero) |
| DB prod | `Sentinela_V18` (100+ clientes) — el nombre real lleva el prefijo, NO es solo "V18" |

> **Dos contenedores web, un postgres.** `odoo18-migration-web-1` es PROD; `odoo-lab`
> es el lab que ves en el navegador `:8075`. El `-u` se corre con `docker exec
> odoo18-migration-web-1 odoo -u ... -d <DB>` (ese binario alcanza ambas DBs). Pero el
> worker que RENDERIZA el lab en el navegador es `odoo-lab`: si validas STAGING por GUI,
> reinicia **`odoo-lab`** (no `odoo18-migration-web-1`) para que recargue el Python.

> Si el módulo es `golfbookvip` (`/opt/golfbookvip/`) o `aleasystem.io`
> (`/opt/aleasystem.io/`): NO es flujo Odoo. Tras rsync, el deploy es
> `docker compose build frontend && docker compose up -d frontend` (un `restart`
> sin rebuild deja el bundle `.next` viejo). El resto de esta skill aplica a addons Odoo.

## Pasos

### 0. Saber qué se cambió
- `git status` / `git diff --stat` para confirmar módulo y archivos.
- ¿El cambio toca **cualquier código Python** — campos (`fields.*`), **métodos nuevos**,
  **modelos/wizards nuevos**, controllers, o cualquier `.py` importado al arranque? → habrá
  que **reiniciar el contenedor web** (paso 4/5). El `-u` actualiza el esquema/registro en la
  DB, pero el proceso Odoo VIVO conserva el Python que importó al arrancar: un método/modelo
  nuevo da `AttributeError`/`OwlError` hasta el reinicio. Solo vistas/datos XML/CSV no lo
  requieren (basta el `-u`). **En la duda, reinicia.**

### 1. ⚠️ Antes de sobreescribir: ¿el server tiene algo más nuevo?
El flujo correcto es repo→server, pero **históricamente no siempre se respetó**
(caso real: `cfdi_prodigia` tenía 452 líneas reales en server vs 71 de stub en repo).
Antes de un rsync que pueda destruir trabajo del server, comparar:
```bash
ssh egarza@192.168.3.2 "wc -l /home/egarza/odoo18-migration/addons/<modulo>/<archivo_sensible>.py"
```
Si el server tiene MÁS líneas/lógica que el repo en módulos sensibles (cfdi, facturación,
firma), **detente y avisa** — primero rescatar al repo, no sobreescribir.

### 2. Dry-run del rsync
```bash
rsync -avzcn --delete --exclude='__pycache__' --exclude='*.pyc' \
  -e "ssh -p 2222 -i $HOME/.ssh/id_rsa_sentinela -o StrictHostKeyChecking=no" \
  "/mnt/c/Users/dell/DellCli/<modulo>/" \
  "egarza@192.168.3.2:/home/egarza/odoo18-migration/addons/<modulo>/"
```
Revisar la lista. Si aparece borrado de algo inesperado por `--delete`, parar.

### 3. rsync real (quitar la `n`)
```bash
rsync -avzc --delete --exclude='__pycache__' --exclude='*.pyc' \
  -e "ssh -p 2222 -i $HOME/.ssh/id_rsa_sentinela -o StrictHostKeyChecking=no" \
  "/mnt/c/Users/dell/DellCli/<modulo>/" \
  "egarza@192.168.3.2:/home/egarza/odoo18-migration/addons/<modulo>/"
```
**`-c` (checksum) es obligatorio.** Sin él, rsync compara por mtime/size y el FS
WSL sobre NTFS tiene timestamps no confiables → puede saltarse archivos cambiados
(bug real: solo transfirió el manifest, dejó el .py viejo → bug silencioso).

Verificar que un símbolo nuevo llegó (no asumir):
```bash
ssh egarza@192.168.3.2 "grep -c '<simbolo_nuevo>' /home/egarza/odoo18-migration/addons/<modulo>/<archivo>"
# debe devolver > 0
```

### 4. Actualizar en STAGING primero
```bash
ssh egarza@192.168.3.2 "sudo docker exec odoo18-migration-web-1 \
  odoo -u <modulo> -d Sentinela_STAGING --stop-after-init"
```
Revisar el output por tracebacks. El `-u` se corre SIEMPRE con `odoo18-migration-web-1`
(ese binario alcanza la DB de staging). Si tocaste Python (paso 0), reinicia el contenedor
que vas a validar:
```bash
# Si validas STAGING por NAVEGADOR (http://192.168.3.2:8075) → reinicia el LAB:
ssh egarza@192.168.3.2 "sudo docker restart odoo-lab"
# (el -u actualiza la DB pero el worker del lab conserva el Python viejo →
#  AttributeError 'método no existe' / OwlError hasta el reinicio)
```
⚠️ Trampa real: el `-u` lo corres en `odoo18-migration-web-1`, pero quien renderiza el
navegador del lab es `odoo-lab`. Reiniciar el contenedor equivocado = "sigue igual".
Confirma que reinició de verdad: `docker ps --filter name=odoo-lab` debe decir "Up X seconds".

### 5. Solo si STAGING quedó limpio: actualizar PROD (`Sentinela_V18`)
**5a. Respaldo previo** (no negociable en prod):
```bash
ssh egarza@192.168.3.2 "sudo docker exec odoo18-migration-db-1 \
  pg_dump -U odoo -Fc -d Sentinela_V18 -f /tmp/Sentinela_V18_pre_<feature>_<fecha>.dump && \
  sudo docker cp odoo18-migration-db-1:/tmp/Sentinela_V18_pre_<feature>_<fecha>.dump /home/egarza/"
```
**5b. Pre-flight del lock conocido** (`product_template`): si `base_unit_count` quedó
`NOT NULL` (drift de migración) o hay conexiones `idle in transaction` (zombie Syscom),
el `-u` se cuelga/falla. Limpiar ANTES:
```bash
# base_unit_count debe ser nullable:
ssh egarza@192.168.3.2 "sudo docker exec odoo18-migration-db-1 psql -U odoo -d Sentinela_V18 \
  -c \"ALTER TABLE product_template ALTER COLUMN base_unit_count DROP NOT NULL;\""
# matar idle-in-transaction si los hubiera (ver reference_deploy_lock_product_template)
```
**5c. `-u` en prod:**
```bash
ssh egarza@192.168.3.2 "sudo docker exec odoo18-migration-web-1 \
  odoo -u <modulo> -d Sentinela_V18 --stop-after-init"
```
**5d. Reiniciar el web de PROD** si tocaste Python (paso 0). Aquí el contenedor es
`odoo18-migration-web-1` (PROD lo sirve él, NO `odoo-lab`). Es un corte breve (~10-20s):
```bash
ssh egarza@192.168.3.2 "sudo docker restart odoo18-migration-web-1"
```

### 6. Verificar versión cargada y reportar
```bash
ssh egarza@192.168.3.2 "sudo docker exec odoo18-migration-db-1 \
  psql -U odoo -d Sentinela_V18 -t -c \
  \"SELECT latest_version FROM ir_module_module WHERE name='<modulo>';\""
```
Confirmar que coincide con la versión del manifest. Reportar el resultado **real**
(versión en DB + si hubo restart). Si la versión NO avanzó, lo más probable es que
el rsync no llegó (server vio el manifest viejo).

## Salvaguardas (no negociables)
- **Nunca** saltar el rsync. El `-u` sin rsync corre código viejo y la versión no avanza.
- **Siempre** `-c` en rsync.
- **Siempre** STAGING antes que `Sentinela_V18`.
- **Respaldo previo** (`pg_dump`) antes de cualquier `-u` en `Sentinela_V18`.
- **Reiniciar el contenedor web tras CUALQUIER cambio de Python** (campos, métodos, modelos/
  wizards nuevos, controllers). El `-u` actualiza la DB; el worker vivo NO recarga el Python.
  Contenedor correcto: `odoo-lab` para el lab por navegador (:8075), `odoo18-migration-web-1`
  para prod. Verifica el reinicio real ("Up X seconds"). En la duda, reinicia.
- El nombre de la DB de prod es **`Sentinela_V18`** (no "V18" a secas).
- Antes de sobreescribir módulos sensibles, comparar contra el server (no vaya a estar más nuevo).
