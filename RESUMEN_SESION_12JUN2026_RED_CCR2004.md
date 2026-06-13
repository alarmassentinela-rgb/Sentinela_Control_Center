# Resumen de sesión — 12 de junio de 2026 (Red / Cutover CCR2004 + Monclova + FFW)

> Sesión separada de la de golfbookvip del mismo día. Aquí: infraestructura de red.

## 1. ⭐ CUTOVER CCR2004 — separación Servidor / WISP (EJECUTADO)
Se ejecutó la separación del servidor a su router propio. **Éxito, downtime real ~2-3 min.**

**Estado final:**
- **CCR2004** (CCR2004-16G-2S+, serial HKF0AMHYZST, ROS 7.19.5) = router del servidor + Empresarial + FFW.
  - ether1: WAN Empresarial (`192.168.100.2/24` + `187.251.199.98/29` + `.99/29`, gw `.97`)
  - ether2: LAN servidores, gateway `192.168.3.254/24`
  - ether3: FFW `10.99.99.1/29`
  - ether4: Trunk `192.168.20.1/30`
  - Rutas: default→`.97`; `10/8`+`172.16/12`+`192.168/16`→trunk (`192.168.20.2`). NAT: masquerade `.98`, FFW 1:1, dst-nat entrantes.
- **Balanceador CCR1009** = WISP puro. Trunk en **ether6** (`192.168.20.2/30`, **fuera de listas WAN/LAN** a propósito — ambas tienen masquerade que rompería el retorno). ether7 quedó idle sin IP.
- **WISP, Monclova, Argus**: sin tocar.

**Decisión técnica clave (la trampa):** el trunk NO va en ether7 (arrastra el PCC del LAN); va en ether6 fuera de las interface-lists, así el tráfico interno del servidor usa la **tabla main limpia** sin marcado PCC ni NAT. Las listas WAN y LAN tienen masquerade (`*1`/`*19`) que habrían NATeado el retorno y roto el ruteo interno.

**Verificación real (post-cutover):** internet (egress `187.251.199.98` ✓), entrantes Odoo (probado desde celular ✓), receptor alarmas/n8n escuchando ✓, interno CCRsentinela/Monclova/sectoriales ✓, FFW Wave `.3/.4` ✓.

**Secuencia ejecutada:** prep trunk ether6 (cero impacto) → cable trunk (⚠️ ether6 estaba admin-disabled, por eso no levantaba) → ping trunk OK → mover handoff TotalPlay→CCR2004 ether1 + FFW→ether3 → encender ether1/ether3 (gw `.97`+internet OK a la 1ª) → mover gateway (`.254` Balanceador ether7→CCR2004 ether2) → verificar → limpiar Balanceador.

**Limpieza Balanceador (reversible):** deshabilitados (NO borrados) 11 NAT + 7 mangle (incluye pineos servidor `*5E/*20/*21`) + 4 IPs (`.98/.99/100.2` ether4, `10.99.99.1` ether5). **Backup previo:** `ccr1009_pre_cutover_12jun.backup`. **Rollback** = re-cablear + re-habilitar.

**Anomalía no-crítica:** server→`10.10.10.11` (appliance UISP) falla — su **firewall propio** rechaza al server (NO es ruteo/NAT: el conntrack confirma masquerade a `192.168.10.254`; `192.168.3.200` y el acceso externo `.98:8443` sí entran). Cloud-managed, se arreglaría en la consola UISP. No bloquea operación.

## 2. Monclova — reconciliación en Odoo (sin tocar el router)
- **Router CCRMonclova** dado de alta en Odoo prod (`sentinela.router` id=4, `172.16.50.1:8728`, `sync_active=FALSE`, prefix `mva`, pppoe_server `pppoe_server1`).
- **Inventario PPPoE Monclova:** 2 cuentas gestión (no clientes) + 9 clientes WISP. **4 activos dados de alta como CORTESÍA (sin cobro)**: SUB-0420 mva0002 (20MB), SUB-0421 mva0009 (20MB), SUB-0422 mva0008 (5MB), SUB-0423 cta0225 (15MB). `billing_mode=courtesy` → excluido de crones de facturación/cobranza por código. Partners placeholder (PENDIENTE nombres reales).
- **5 restantes = bajas definitivas** (mva0004/05/06/07/10), no se reconcilian.
- **Monclova corre Argus** (ISP 1465 Telmex) → migrar = mismo patrón Argus→Odoo.
- **6 perfiles de internet sincronizados a Monclova** (`argusblack_plan_841_1796…1801`) vía `action_sync_to_routers` apuntando solo a CCRMonclova.
- **Ciclo provisioning validado end-to-end** (alta/suspender/reactivar/baja) con SUB-0002 de prueba + secret `mva9999` (creado/probado/borrado; 11 secrets reales intactos). Diagnóstico (tráfico vivo + señal antena) funciona desde el server. Falta para operar: prender `sync_active` tras reconciliar.

## 3. FFW — acceso, salud del enlace y monitoreo
- **Acceso confirmado** a las 2 Wave (`10.99.99.3` Oficina / `10.99.99.4` Maquiladora) por API HTTP (`sentinela/SentinelaW1sp#`).
- **Salud del enlace:** radio sano ~1.62 Gbps, señal -63/-65 dBm (MCS 8/QPSK, ideal 12), distancia 4.69 km. **🔴 Cuello de botella:** el puerto ethernet de la Wave `.4` negocia a **100M con 510 errores** → tope ~83M. Cambiar cable en sitio FFW (sigue pendiente físico).
- **Monitoreo montado en netwatch:** `leer_waves_ffw()` cada ~5 min (login API → `/statistics`), alerta a Telegram por cambio (enlace caído / eth <1000M / señal degradada). **Tarjeta FFW en el dashboard NOC** (`:8090`). Desplegado (`vigilante.py` + `dashboard.html` rsync + restart).

## 4. PDFs enviados a Telegram
- `ARQUITECTURA_RED_MONCLOVA_12JUN2026.pdf` — topología/VPN/administración Monclova.
- `ARQUITECTURA_RED_SENTINELA_POST_CCR2004_12JUN2026.pdf` — red completa tras el cutover (segmentos, routers, flujos, antes/después).

## Pendientes para la próxima
1. **Monclova:** poner nombres fiscales reales a los 4 partners de cortesía; reconciliar y prender `sync_active` cuando se decida cobrar. Procesar formalmente las 5 bajas (opcional, borrar secrets).
2. **FFW:** cambiar el cable/puerto de la Wave `.4` en sitio (100M→1000M) para liberar el tope de 83M.
3. **Balanceador:** desconectar el cable de ether7 del switch (idle); cuando el cutover lleve días estable, borrar definitivo lo deshabilitado (hoy solo disabled = rollback).
4. **UISP `.11`:** si el server llegara a necesitarlo, ajustar el firewall del appliance en la consola cloud (no es red).
5. **EdgeSwitch VLANs** (pendiente histórico, no se tocó hoy).

## Verificaciones SIN validar
- Entrantes alarmas: el receptor `:10001` escucha y el dst-nat está, pero no llegó una señal real durante la sesión para confirmar end-to-end (Odoo entrante sí se probó desde celular).
- FFW tráfico de cliente: la maquiladora ya había salido (enlace ocioso), no se probó tráfico real de cliente por el `.99`.
