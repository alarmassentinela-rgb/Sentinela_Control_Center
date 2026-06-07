# HANDOFF — Balanceo PCC del Balanceador (trabajo de madrugada)

> Documento auto-contenido para retomar el balanceo WISP en una ventana de tráfico bajo.
> Última sesión: 7-jun-2026 (madrugada). Estado: **clientes seguros en ISP1, balance pendiente.**

## 0. Acceso / red (verificar primero)
- **Balanceador (donde se trabaja):** `192.168.10.254`, API 8728, user `gemini_api`, pass `gemini_api2113`.
- **CCRsentinela:** `192.168.10.50` (mismas credenciales).
- Desde casa: estás en la red local vía antenas **EnlaceBase-EG (192.168.3.200/3.201)**. Verifica alcance:
  ```
  python3 -c "import socket; s=socket.create_connection(('192.168.10.254',8728),5); print('Balanceador OK'); s.close()"
  ```
- Server Odoo/SSH: `ssh -p 2222 -i ~/.ssh/id_rsa_sentinela egarza@192.168.3.2` (no se usa para esto).
- Lib Python: `pip install routeros_api` (o `routeros-api`).

## 1. DÓNDE QUEDAMOS (estado actual)
- **Clientes WISP: TODOS en ether1 (ISP1, ~240 Mbps), funcionando.** Estado seguro/normal.
- `failoverConfig` global `foIsps = {{1;1}}` (solo ISP1). **ether2 APAGADO.**
- Reglas NAT por interfaz **ether2/ether3 ya agregadas** (comment "PCC: NAT por interfaz"). Falta ether1 (opcional, jala por catch-all).
- Rutas: recursivas activas (sirven), directas de Argus deshabilitadas.

## 2. LO QUE YA ESTÁ PROBADO (no re-discutir)
- ✅ **Infraestructura BUENA:** PC de oficina 192.168.3.90, ruteada a to_ISP2 y to_ISP3 con flush de su conntrack, **navegó PERFECTO** por ether2 (NAT 192.168.2.50) y ether3 (NAT 192.168.0.50), descargas bidireccionales completas.
- ✅ El PCC marca bien el 2:1:2 (denom 5: 5/0,5/1→ISP1 / 5/2→ISP2 / 5/3,5/4→ISP3).
- ✅ Rutas recursivas y NAT por interfaz: correctos.
- ✅ Diagnóstico CONFIABLE = **conntrack** (campo `reply-dst-address` = IP de origen NAT; `repl-bytes` = datos de vuelta). Los **ping por API NO sirven** (falsos negativos).

## 3. EL ÚNICO PROBLEMA POR RESOLVER
Al aplicar el balance a los clientes (foIsps 2:1:2 + flush): las conexiones WISP **se marcan bien** (ISP3_conn, ISP2_conn) **pero TODAS egresan ether1** (NAT-src 192.168.1.50; ether2/ether3 en 0). 
- La **PC por ether7** con marca idéntica SÍ sale por ether3.
- El **WISP por combo1** (src 192.168.10.50, NATeado por el CCR) NO.
- Verificado: la regla mark-routing `#45` (cm=ISP3_conn → to_ISP3) tiene `in-interface-list=LAN`, y **combo1 SÍ está en la lista LAN**. Aun así no rutea por ether3 para el WISP.
- **Hipótesis a investigar:** timing del 1er paquete bajo alto churn; o algo del path del CCR-NAT (combo1) distinto a ether7; o una regla previa que toca el tráfico combo1.

## 4. PLAN PARA LA MADRUGADA
1. **Re-validar con la PC** que la infra sigue bien (script `test_setup.py` → 192.168.3.90 a to_ISP3 + flush, monitorear). Confirma punto de partida.
2. **Aislar combo1 vs ether7:** marcar SOLO el tráfico de combo1 (o una IP de cliente de prueba detrás del CCR) y trazar conntrack: ¿se le aplica la routing-mark? ¿sale por ether3? Comparar el recorrido de mangle entre un paquete ether7 y uno combo1 (usar `/tool sniffer` o contadores de reglas mangle: ver qué regla incrementa para cada uno).
3. **Comparar con Argus original:** el backup `pre_pcc_redesign.backup` (en el router, 25-may) tenía el WISP balanceado funcionando. No se pudo leer por API (muy grande). En la madrugada: exportar/leer ese .rsc (o `/import` en un router de prueba) y ver cómo Argus manejaba el tráfico de combo1/WISP (¿regla específica? ¿otra estructura de mangle?). Probable que el "rediseño" 26-may rompió justo eso.
4. **Cuando se resuelva:** aplicar foIsps 2:1:2 + flush conntrack WISP (`flush_wisp.py`, correr en background — son ~7000 conex, lento por API) → monitorear que ether2/ether3 suban y total se mantenga. Si no, rollback.

## 5. SCRIPTS (en esta carpeta)
- `test_setup.py` / `test_wispstyle.py` / `test_ether2.py` — rutean SOLO 192.168.3.90 por to_ISP3/to_ISP2 + flush (prueba sin tocar clientes).
- `apply_balance_final.py` — aplica 2:1:2 + flush + monitor + auto-rollback. **⚠️ corregir antes:** el `re.sub` de foIsps es non-greedy y CORROMPE la línea; usar reemplazo de LÍNEA COMPLETA (split por `\n`, reemplazar la línea con `global foIsps`).
- `restore_argus.py` — habilita rutas directas de Argus + 2:1:2 (mismo bug de regex, corregir).
- `flush_wisp.py` — vacía conntrack de 192.168.10.50 (correr en background).
- `capture_restore.py`, `review_argus_pcc.py`, `check_nat_ether3.py` — diagnóstico/captura.

## 6. ROLLBACKS (en la raíz del repo) — para dejar TODO como estaba
- `ROLLBACK_PCC_07JUN2026.py` — revierte cambios de rutas/NAT/ether2 a recursivas + ISP1.
- `ROLLBACK_RESTORE_ARGUS_07JUN2026.py` — revierte el intento de rutas directas.
- **Reverso manual rápido a ISP1 seguro:** poner `foIsps={{1;1}}` en failoverConfig (reemplazo de línea completa), correr scripts `failoverConfig` + `failoverActualizadorCapacidadesISPs`, apagar ether2 (interface id `*3`).
- `failoverConfig_ORIGINAL_07JUN2026.rsc` — config previa (5 ISP) de referencia. **NO restaurar tal cual** (reincluye ISP3/5/6 que rompen).

## 7. CÓMO FUNCIONA EL FAILOVER DEL BALANCEADOR (para no romperlo)
- Schedulers `foSchedule1/2` cada 10s → `failover` → corre `failoverConfig` (define `foIsps={{id;peso}}`, `foIpDNS=208.67.222.222`) → pinga cada ISP → `failoverActualizadorCapacidadesISPs` reconstruye las reglas PCC (denominador = suma de pesos) → `failoverActualizadorReglasMangle` habilita/deshabilita por caídos.
- **El control del PCC es `foIsps` en failoverConfig, NO editar reglas mangle a mano (se sobrescriben en 10s).**
- Mapa WAN: ether1=Telmex(ISP1), ether2=TotalPlay(ISP2), ether3=Telmex(ISP3), ether4/5=TotalPlay Empresarial IP fija + FFW (NO al PCC), ether6=libre, ether7=oficina.
- Pesos que quiere Enrique: **2:1:2** (Telmex 40%+40%, TotalPlay 20%).
- ⚠️ **Receptoras de alarma** (192.168.3.91: CNORD/TEKO/Honeywell) entran SOLO por ether1 — punto único de falla aparte, pendiente.

## 8. LECCIONES DE TOOLING (no repetir errores)
- `re.sub(':global foIsps \\{.*?\\};')` non-greedy CORROMPE la línea. Usar split por líneas.
- Flush de conntrack por API es LENTO (~7000 conex → timeout). Correr en background.
- Ping por API = falsos negativos. Usar conntrack.
- Editar source de script: `api.get_resource('/system/script').set(id=..., source=...)`.
- Correr script en el router: `api.get_binary_resource('/system/script').call('run', {'number': b'nombre'})`.
