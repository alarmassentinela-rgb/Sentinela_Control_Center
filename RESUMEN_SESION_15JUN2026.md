# Resumen de sesión — 15 de junio de 2026

## Suscripciones GPS — Automatización de comandos SMS (sentinela_subscriptions 18.0.1.3.90 → 18.0.1.3.93)

Continuación del producto GPS/SentiCar. Hasta hoy el comando SMS al rastreador era
**texto libre tecleado a mano**; ahora hay un catálogo de plantillas que arma el comando solo.

### v18.0.1.3.91 — Catálogo de comandos SMS GPS (commit `1a91fbd`)
- **Modelo nuevo `sentinela.gps.command.template`** (`models/gps_command.py`): plantilla por
  **familia** (Concox/GT06, Coban, Teltonika, genérico) y **acción** (APN, Servidor, Estado,
  Ubicar, Intervalo, Reset, Factory, Relay corte-motor, Otro). Campos: `command_template`
  (con placeholders), `default_port`, `encoding`, `sequence`, `note`. Método
  `render_for_device(device)` resuelve los placeholders.
- **Placeholders:** `{apn}` (param `sentinela.gps_apn`), `{server}` (por plataforma de la sub,
  params `sentinela.gps_server_senticar/_tracksolid/_smake`), `{port}` (de la plantilla),
  `{pwd}` (campo nuevo `gps_password` del equipo, default 666666), `{imei}`.
- **En el equipo (`gps_device.py`):** campos nuevos `gps_password` + `gps_command_template_id`;
  `@onchange` arma `gps_sms_command`+`gps_sms_encoding` al elegir plantilla; al enviar OK limpia
  comando y selector. NO hay auto-send (por seguridad: el operador revisa antes de "Enviar SMS").
- **Config + catálogo:** 4 campos en Ajustes; menú *Configuración → Comandos SMS GPS* (manager);
  ACL user solo-lectura / manager full. Seed inicial de plantillas N01K/GT06 + Coban.
- **Verificación V18:** versión 18.0.1.3.91 en DB, modelo registrado, seed cargado.

### v18.0.1.3.92 — {server} = DOMINIO (no IP cruda) (commit `d30d189`)
- A petición de Enrique: el servidor del comando usa el **dominio `gps.senticar.com`** y NO la
  IP fija, para que un cambio de IP solo toque el registro A (sin reconfigurar todos los GPS).
- Verificado por DNS: `gps.senticar.com` → 187.251.199.98 (DNS-only). `radar.senticar.com` va
  proxied por Cloudflare → NO sirve para el TCP crudo del GPS.
- Param `sentinela.gps_server_senticar` = `gps.senticar.com` y `gps_apn`=`gigsky-02` sembrados
  en `data/gps_command_data.xml`.
- **Comando GT06 corregido a MODO 1 (dominio):** `SERVER,1,{server},{port},0#` (el N01K
  distingue IP=modo 0 vs dominio=modo 1; en modo 0 con dominio lo rechaza). Puerto 5023.
- ⚠️ **Gotcha noupdate:** los seeds tienen `noupdate="1"` → editar el XML NO repisa las
  plantillas ya instaladas. El registro `gps_cmd_gt06_server` (creado en v.91 con modo 0) se
  corrigió por **SQL directo en STAGING + V18**. Para cambiar un seed ya desplegado: UI o SQL.
- **Verificación V18:** versión .92, params correctos, plantilla en `SERVER,1,{server},{port},0#`.

### v18.0.1.3.93 — Botones GPS junto a su sección (commit `848e2c3`)
- Reubicados los botones del form de equipo: **📨 Enviar SMS** → en "Comando SMS";
  **🔄 Actualizar diagnóstico** → en "Diagnóstico SIM"; **📍 Generar link** → en "Compartir
  rastreo". En la cabecera quedan solo las acciones de estado/ciclo (Suspender/Reactivar/
  Registrar) con el statusbar.
- **Verificación V18:** versión .93, STAGING+V18 limpios. Cambio solo de vista.

### Deploy (todas)
release-modulo (commit+tag+push) + deploy-modulo (rsync→`-u` STAGING→`-u` V18→verificar).
Tags `v18.0.1.3.91/.92/.93-sentinela_subscriptions`. Restart del container web en .91 (campos
Python/modelo nuevo). DB V18 confirmada en 18.0.1.3.93.

## Pendientes para la próxima sesión
1. **Probar real** una plantilla en un N01K de la flota (SUB-0385): elegir "Configurar
   Servidor" y verificar que arme `SERVER,1,gps.senticar.com,5023,0#` y llegue por GraphQL
   floLIVE. **Sin validar** end-to-end aún.
2. **Capturar ICCID** en las subs GPS de clientes reales (sin ICCID no aplica diag/SMS/registro).
3. Limpiar cuentas DEMO de la jerarquía SentiCar (Grupo SentiCar id7, Distribuidor Demo id8,
   Subcliente A/B id9/10).
4. Persistencia Traccar (DB H2 + assets web a volúmenes antes de recrear `traccar-server`).
5. Fase C/D SaaS (Stripe en vivo), automatizar reseller, iOS.

## Otro (fuera de esta sesión)
- Hoy también hubo releases de **sentinela_monitoring v18.0.1.13.0 → .13.6** (rediseño de la
  ventana de atención) en otra sesión — ver git log; no documentadas aquí.

## Archivos sueltos sin commitear (heredados, NO de esta sesión)
`sentinela_subscriptions/data/ir_cron_data.xml` y `views/mikrotik_profile_views.xml`
(cambios WISP referencian v.67; el server ya los tiene idénticos, el repo va detrás). Pendiente
decidir si se commitean.
