---
name: cargar-gps-flota
description: >-
  Carga en bloque los GPS de un cliente desde un Excel (de Descargas, formato
  export de Smake/Connecta) hacia una suscripción de sentinela_subscriptions, y
  reconcilia/valida cada SIM contra Connecta (floLIVE) por IMEI. Úsalo cuando
  Enrique diga "carga los gps del archivo X a SUB-YYYY", "agrega los gps de ...",
  "se quedan en smake" o "migrar a senticar". Cubre el alta de equipos, el cruce
  IMEI↔SIM autoritativo desde floLIVE (rellena SIMs faltantes, corrige las malas),
  y opcionalmente la migración completa a SentiCar (registrar en Traccar + SMS).
---

# Cargar flota GPS a una suscripción + validar SIMs en Connecta

Tarea recurrente al migrar clientes de GPS: meter sus equipos (de un Excel export
de Smake/Connecta) a su `sentinela.subscription`, dejar el cruce IMEI↔SIM correcto
(autoridad = Connecta/floLIVE), y según el caso dejarlos en **Smake** o **migrar a
SentiCar**.

## Coordenadas
- **Odoo XML-RPC:** `http://192.168.3.2:8070`, DB `Sentinela_V18`, user `api_user`
  (password en memoria `reference_credentials_index` — NO hardcodear aquí).
- **Excel:** en `/mnt/c/Users/dell/Downloads/` (WSL). Nombre tipo `<cliente> gps.xlsx`.
  ⚠️ Hay archivos casi-homónimos y `~$...` (locks de Excel, ignorar). Confirma cuál es
  el más nuevo si hay duda (Enrique a veces se equivoca al guardar el nombre).
- **floLIVE/Connecta y Traccar:** se consultan por `odoo shell` en PROD (ver más abajo).

## Formato del Excel (export Smake/Connecta, hoja "SheetJS")
| col | índice | campo |
|---|---|---|
| D | 3 | **IMEI** (lo importante; familia Concox/GT06 N01-4/N01H/N01K) |
| E | 4 | **Nombre del dispositivo** → alias del equipo |
| H | 7 | **SIM** (ICCID limpio, 19 díg `8935711001...`) |
| I | 8 | "ICCID" con **`f` final basura** → NO usar, usar col H |

Parsear con `openpyxl` (`data_only=True`). Saltar el encabezado (fila 0).

## Pasos

### 1. Leer el Excel y la suscripción
- Parsear filas (IMEI, nombre, SIM). Reportar cuántos equipos, cuáles sin SIM, y SIMs
  malformadas (no empiezan en `8935711` o ≠19 díg).
- Leer la sub: `partner_id`, `service_type` (debe ser `gps`), `gps_platform`,
  `gps_mode`, `product_id`, equipos actuales.

### 2. Definir plataforma de la sub (gps_platform)
- Si Enrique dijo destino ("se quedan en smake" / "migrar a senticar"), úsalo.
- Si la sub trae `gps_platform` vacío o **incoherente con el producto** (típico:
  producto `[MON8] ...TRACKSOLID` pero el cliente está en Smake), **PREGUNTA** antes
  de setear (smake / tracksolid / senticar). No asumas.
- `gps_platform` es un campo directo y editable (write).
- ⚠️ `gps_mode` es `related` de `product_id.gps_mode` (NO editable directo). Productos de
  monitoreo (MBASICO) lo traen vacío → los equipos quedan con modo en blanco; no estorba
  (el registro a SentiCar no pide modo; el SMS solo se bloquea si el modo es `movil`).
- ⚠️ Si seteas plataforma ≠ a la del producto, queda inconsistencia plan↔plataforma:
  AVÍSALO (hay que corregir el producto después, importa para facturación).

### 3. Anti-duplicado y alta de equipos
- El constraint único es por **`gps_imei`** (NO por `sim_iccid` — una SIM mal capturada
  puede aparecer en 2 equipos sin que truene). Antes de crear, busca esos IMEI en
  `sentinela.subscription.gps.device`; si alguno ya existe, repórtalo y NO lo dupliques.
- Crear cada equipo: `{subscription_id, name, gps_imei, sim_iccid}`. El `gps_platform`
  del equipo es `related` de la sub → se llena solo.

### 4. Validar/reconciliar SIMs en Connecta (floLIVE) — el "camino de validación"
Autoridad del cruce IMEI↔SIM = floLIVE. **floLIVE NO deja listar por cuenta**
(`/api/v2/subscriber` da 500 "No static resource"), **pero sí busca por IMEI**:
`GET https://floportal.flolive.net/api/v2/subscriber/imei/{imei}` →
`content[0].subscriberIdentifiers.iccid` (+ `alias`, `subsStatus`). El `alias` suele
codificar el IMEI ("Cliente Gps <últimos díg del IMEI>") → sirve de doble-check.
- Para cada equipo: lookup por IMEI → si floLIVE trae un ICCID distinto (o el equipo
  venía sin SIM), **rellena/corrige** `sim_iccid` con el de floLIVE.
- `subsStatus=SUSPEND` (o 403 al mandar SMS) = SIM suspendida en floLIVE.
- **Correr por `odoo shell` en PROD** (los métodos floLIVE no son `@api.model` y truenan
  por XML-RPC con marshalling de None):
```bash
ssh -p 2222 -i $HOME/.ssh/id_rsa_sentinela egarza@192.168.3.2 \
  "sudo docker exec -i odoo18-migration-web-1 odoo shell -d Sentinela_V18 --no-http 2>/dev/null" <<'PYEOF'
import requests
svc=env['sentinela.flolive.service']; tok=svc._get_auth_token()
H={"Authorization":f"Bearer {tok}"}; B="https://floportal.flolive.net/api/v2"
sub=env['sentinela.subscription'].search([('name','=','SUB-XXXX')])
for d in env['sentinela.subscription.gps.device'].search([('subscription_id','=',sub.id)]):
    r=requests.get(f"{B}/subscriber/imei/{(d.gps_imei or '').strip()}",headers=H,timeout=20)
    if r.status_code==200:
        c=r.json().get('content'); c=c[0] if isinstance(c,list) and c else c
        flo=((c or {}).get('subscriberIdentifiers') or {}).get('iccid')
        if flo and flo!=(d.sim_iccid or ''):
            d.sim_iccid=flo  # rellena/corrige
env.cr.commit()
PYEOF
```

### 5. (Opcional) Migrar a SentiCar — solo si está AUTORIZADO
Mismo flujo que la migración KAWAC (ver memoria `project_kawac_migracion_senticar`):
1. `gps_platform='senticar'` en la sub.
2. Por equipo: `action_register_senticar` (crea device en Traccar + usuario/grupo del
   cliente). ⚠️ Lanza un Fault de XML-RPC al final del request **pero el `senticar_device_id`
   ya commitea** → queda OK; verifica leyendo `senticar_device_id`/`senticar_state`.
3. Cutover físico por SMS (GT06): plantilla `concox_gt06/set_server` =
   `SERVER,1,gps.senticar.com,5023,0#` (modo 1=dominio, puerto Traccar GT06 5023).
   Setear `gps_command_template_id`+`gps_sms_command` y `action_send_sms` por equipo.
4. Verificar en Traccar que conecten (`http://192.168.3.2:8082`, creds en
   `ir.config_parameter sentinela.traccar_api_*`): `/api/devices?all=true` →
   `status=online`/`lastUpdate≠null`. Posición `0,0` al inicio = login sin fix GPS (normal).

## Trampas (resumen)
- Constraint único = **IMEI**, no SIM. Dedup por IMEI.
- Col ICCID del Excel trae `f` final → usar col **SIM** (H).
- `gps_mode` viene del producto (related), no se setea directo.
- Producto Tracksolid/Monitoreo con plataforma puesta a smake/senticar = inconsistencia a corregir.
- floLIVE: no hay listado; **lookup por IMEI** sí. Correr por odoo shell (no XML-RPC).
- Logs del contenedor en hora **LOCAL (CST)**, no UTC.
- NO migrar a SentiCar sin autorización explícita ("aún no me autorizan" → dejar en Smake).
