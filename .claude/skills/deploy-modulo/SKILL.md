---
name: deploy-modulo
description: >-
  Despliega un módulo sentinela_* (o golfbookvip / aleasystem.io) al servidor
  de producción 192.168.3.2. Úsalo cuando se editó código de un addon y hay que
  aplicarlo en el server. Encadena rsync (local→server) → docker -u en STAGING →
  docker -u en V18 → verificación. El server NO es git working tree: sin rsync,
  el `-u` corre código viejo. Para crear el commit/tag/push antes de desplegar,
  usa primero la skill release-modulo.
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
| Container web | `odoo18-migration-web-1` |
| Container db | `odoo18-migration-db-1` |
| DB staging | `Sentinela_STAGING` (validar SIEMPRE primero) |
| DB prod | `Sentinela_V18` (100+ clientes) |

> Si el módulo es `golfbookvip` (`/opt/golfbookvip/`) o `aleasystem.io`
> (`/opt/aleasystem.io/`): NO es flujo Odoo. Tras rsync, el deploy es
> `docker compose build frontend && docker compose up -d frontend` (un `restart`
> sin rebuild deja el bundle `.next` viejo). El resto de esta skill aplica a addons Odoo.

## Pasos

### 0. Saber qué se cambió
- `git status` / `git diff --stat` para confirmar módulo y archivos.
- ¿El cambio agrega/elimina **campos Python** (`fields.*`), modifica **controllers**
  o cambia código importado al arranque? → marca que habrá que **reiniciar el container web**
  (paso 4). Cambios solo de vistas/datos XML/CSV no lo requieren.

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
Revisar el output por tracebacks. Si agregaste/quitaste campos Python o tocaste
controllers, además reiniciar el container (el `-u` actualiza la DB pero NO recarga
el Python del proceso vivo → `OwlError: field is undefined`):
```bash
ssh egarza@192.168.3.2 "sudo docker restart odoo18-migration-web-1"
```

### 5. Solo si STAGING quedó limpio: actualizar PROD (V18)
```bash
ssh egarza@192.168.3.2 "sudo docker exec odoo18-migration-web-1 \
  odoo -u <modulo> -d Sentinela_V18 --stop-after-init"
# + restart si aplica (paso 4)
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
- **Siempre** STAGING antes que V18.
- **Reiniciar el container web** tras cambios de campos Python / controllers.
- Antes de sobreescribir módulos sensibles, comparar contra el server (no vaya a estar más nuevo).
