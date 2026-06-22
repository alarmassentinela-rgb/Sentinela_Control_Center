# Resumen de sesión — 22 de junio de 2026

## Tema único: Balanceador PCC — restauración del balanceo 50/50 ISP1+ISP3

Sesión completa dedicada a "arreglar el Balanceador PCC". Resultado: **balanceo
multi-WAN ISP1+ISP3 RESTAURADO y funcionando** tras encontrar la causa raíz real
que llevaba meses sin resolverse. Cero microcorte a clientes.

### Punto de partida (creencia previa, resultó FALSA)
La memoria del 14-jun decía "ISP3/Telmex roto, solo llega a 9.9.9.9" → se creía que
no había 2do WAN sano para balancear, y el WISP estaba en **ISP1-único**.

### Diagnóstico (cronología)

1. **El ping por API miente.** `routeros_api /ping interface=etherX` dio 0/4 pingeando
   hasta el módem `192.168.0.254` DIRECTAMENTE conectado a ether3 (ruta connected
   activa). TODOS los diagnósticos previos de "ISP3 roto" salieron de ese ping
   mentiroso → eran falsos.

2. **Prueba directa al módem (Enrique conectó una PC al puerto LAN del módem Telmex,
   brincando el Balanceador):** 0% loss a OpenDNS/Google/Cloudflare/Quad9, HTTP 200,
   IP pública `187.136.185.33`. **La línea Telmex/ISP3 está PERFECTA.** No era el módem
   ni Telmex.

3. **El ruteo `to_ISP3` funciona** (confirmado con ping nativo de Winbox
   `routing-table=to_ISP3` = 5/5 a 1.1.1.1 y OpenDNS; y marcando un host de oficina
   192.168.3.10 que salió por ether3 con la IP Telmex). El problema era específico del
   tráfico masivo de clientes WISP.

4. **Reaplicando 50/50 y midiendo con contadores de interfaz (no ping):**
   ether3 mostró **TX subiendo / RX = 0.00 durante 50s**. Asimetría real, no artefacto.

5. **Causa raíz, confirmada por conntrack `reply-dst-address`:**
   - **(a)** Los clientes WISP llegan al Balanceador como **`192.168.10.50`**, porque
     **CCRsentinela los NATea a su propia IP** antes de pasarlos por el trunk. NO llegan
     como `172.16.10.x` (por eso las pruebas filtrando por IP de cliente daban 0).
   - **(b)** El **clasificador PCC (mark-connection) estaba DEBAJO de las reglas
     mark-routing `*14-*19`.** En el primer paquete de cada conexión nueva: llega sin
     marca → `*16 (cm=ISP3_conn→to_ISP3)` no dispara → el clasificador (al final del
     chain) recién marca `ISP3_conn` → pero la ruta YA se decidió sin routing-mark →
     tabla main → **ether1, y el NAT queda clavado en `192.168.1.50` (ISP1)**. Los
     paquetes siguientes intentan salir por ether3 con el source de ISP1 → Telmex
     descarta → **ether3 RX=0**. Medido: 1073/1081 conexiones ISP3_conn con
     `reply-dst=192.168.1.50`.
   - Esto **ya estaba advertido** en la limpieza del 14-jun: *"el clasificador está
     después de los mark-routing — inocuo con single-WAN, pero hay que subirlo si se
     reactiva multi-bucket."*

### El fix (aplicado, funcionando, persistente)

- Se recreó el ancla **`fo_bandera_pcc`** (regla `passthrough` deshabilitada, inerte)
  y se movió **ARRIBA de `*14`**. El motor de failover
  (`failoverActualizadorCapacidadesISPs`) coloca los buckets en esa ancla
  (`move destination=<ancla>`) → quedan arriba de las mark-routing.
- `foIsps={{1;1};{3;1}}` en el script `failoverConfig` + run → el scheduler armó los
  2 buckets (`both-addresses:2/0→ISP1_conn`, `2/1→ISP3_conn`) en el ancla.
- **Verificado:** buckets en posición 33-34 vs `*14` en 36 (arriba ✓).
- **NO se hizo flush** → las conexiones nuevas salen correctas, las viejas (clavadas a
  ISP1) expiran solas. Cero microcorte.

### Verificación real (en vivo)
- ether3 (ISP3): **RX 0 → ~124 Mbps** de descarga real de clientes.
- ether1 (ISP1): ~113 Mbps. Reparto convergió a ~50/50.
- 976/1010 conexiones ISP3 salen con el source correcto `192.168.0.50` (ether3).
- `foIsps`=`foIspsAnt`=`1;1;3;1` (motor en reposo). `to_ISP3 principal` active=true.
- `failoverConfig` persiste el 50/50 → sobrevive reinicios.

### Trampas aprendidas (para la próxima vez)
- **Ping-API miente** → medir con ping nativo Winbox (`routing-table=to_ISPx`),
  conntrack (`reply-dst-address`), o directo al módem.
- **Conntrack por API:** NO leer toda la tabla (13k conexiones → crashea
  `no such item`); usar filtro server-side `conn.get(connection-mark='ISP3_conn')`.
- **Motor failover frágil por API:** los scripts `failover*` tienen un `foreach` sin
  `:` (línea ~21 de `failoverActualizadorCapacidadesISPs`) que **aborta a media
  reconstrucción** cuando se corre por `system/script/run` (deja el clasificador
  vacío). SOLO funciona vía su scheduler. Balancear = editar `foIsps` en
  `failoverConfig` y dejar al scheduler; NO correr el rebuild a mano.
- **El ancla `fo_bandera_pcc` SIEMPRE debe ir arriba de `*14`** o el fix se rompe.

### Backups del día
- `balanceador_pre_pcc5050_22jun.backup` (binario en el router, PRE-cambios).
- `.backup_failoverConfig_pre5050_22jun.rsc` (local, el `failoverConfig` original).
- Scripts de diagnóstico en la raíz: `diag_pcc_estado_22jun.py`, `diag_wan_salud_22jun.py`.

## Segunda parte: failover TotalPlay (ISP2) si cae Telmex — RESUELTO

Pedido por Enrique: como ISP1 e ISP3 son **ambos Telmex**, una caída regional de
Telmex tiraría las dos → ¿sirve TotalPlay (ISP2/ether2) de respaldo?

**Diagnóstico (mismo patrón que ISP3):**
- ether2 estaba **disabled**. Al habilitarlo, el ping nativo de Winbox al módem
  `192.168.2.254` dio **"host unreachable"** (ARP falla) y a internet 0/4.
- Parecía TotalPlay muerto, PERO conectando una PC **directo al módem TotalPlay**
  (brincando el Balanceador): internet OK, IP pública **`187.190.18.23` (rango
  TotalPlay)** → **la línea funciona perfecto.**
- **Causa raíz:** el módem TotalPlay está en **`192.168.100.0/24` (gateway
  `192.168.100.1`)**, pero ether2 tenía config vieja **`192.168.2.50/24` gw
  `192.168.2.254`** → subred equivocada (el módem se cambió/reseteó; la nota del
  26-may del "cable" era incompleta). No era cable ni línea — **config desfasada.**

**Fix aplicado (dos partes):**
1. **Subred:** el módem TotalPlay está en `192.168.100.0/24` gw `192.168.100.1`; ether2
   tenía `192.168.2.x`. Se corrigió `probe-ISP2` gw → `192.168.100.1`, se limpiaron 3
   rutas legacy con gw `192.168.2.254` y se deshabilitó un default main vía ether2.
2. **Loss del 70-80% = CONFLICTO DE IP, no línea degradada.** Al poner ether2 con IP
   FIJA `192.168.100.50`, esa IP estaba **dentro del pool DHCP del módem** → ARP
   peleado → 70-80% loss. **Prueba clave:** desde una PC directo al módem con DHCP
   (`.5`) = **30/30 0% loss**; con la fija `.50` = pérdida. **FIX: ether2 → cliente
   DHCP** (`add-default-route=no`, `use-peer-dns=no`) → tomó `192.168.100.4` →
   **`to_ISP2 principal` pasó de 3/8 a 8/8 active (estable)** y el ping de prueba
   (8.8.8.8 forzado por /32 vía TotalPlay) = **10/10 0% loss.**
- Rutas `fo-ISP2` (en to_ISP1 y to_ISP3) a **dist=3** → TotalPlay = último recurso
  (solo si caen los DOS Telmex; un Telmex caído usa el otro Telmex dist 2).

**Resultado intermedio:** ether2/TotalPlay quedó reachable y estable, 0% loss.

### Tercera parte: ISP2 ACTIVO en el PCC (balanceo 3-way) + MSS clamp
Enrique decidió meter ISP2 al balance (no solo failover). Al forzar tráfico de prueba
por una ruta /32 manual, una descarga grande **stalleaba** (1 byte) aunque el ping y el
HTTPS chico funcionaban → síntoma de **MTU**. Path-MTU medido por TotalPlay = **1480**
(el módem recorta 20 bytes). **FIX: MSS clamp `new-mss=1440` en ether2** (chain forward,
in+out, tcp syn) — igual que el enlace FFW. (El stall del demo era además agravado por
ir mi tráfico por el trunk+doble-NAT, camino que NO usan los clientes.)
- **foIsps → `{{1;1};{2;1};{3;1}}` (3-way equitativo).** El motor armó 3 buckets
  (`3/0→ISP1`, `3/1→ISP2`, `3/2→ISP3`) arriba de `*14`.
- **Verificado con tráfico REAL de clientes:** ether2 RX subió a varios Mbps; de 629
  conexiones ISP2, **561 con retorno y 141 con descargas reales (>10KB, hasta 5.9 MB)**;
  `reply-dst=192.168.100.4` (ether2) en 318/320 → NAT correcto, NO se fuga a ISP1. El
  bug de ether3 (clasificador) NO se repite porque ya está arriba de `*14`.
- TotalPlay tiene más latencia (50-140ms, Houston) → conexiones ahí algo más lentas pero
  funcionales. Peso ajustable (ej. 2:1:2 Telmex-favorecido) si se quiere que cargue menos.

**Estado final del Balanceador:** **balanceo 3-way ISP1+ISP2+ISP3 activo y sano**, las
3 WAN cargando tráfico real de clientes, clasificador arriba de `*14`, MSS clamp en
ether2, ether2 en DHCP (`192.168.100.4`). Todo persistente. La LÍNEA TotalPlay siempre
estuvo sana; todo era config (subred vieja + IP fija en conflicto con pool DHCP + faltaba
MSS clamp).

## Pendientes para la próxima sesión

1. **No se simuló la caída real de ambos Telmex** — la jerarquía de failover está bien
   en config y las rutas activas/estables, pero el evento end-to-end (ambos Telmex
   abajo → tráfico real por TotalPlay) no se probó en vivo. Validar en una ventana si se
   quiere certeza total.
2. **ether2 quedó en DHCP** (`192.168.100.4`, dinámica). La IP puede cambiar si el
   módem la reasigna; el failover no depende de la IP (usa gw `192.168.100.1` fijo +
   masquerade por interfaz), así que es robusto. Si TotalPlay vuelve a cambiar de
   subred, reconfigurar `probe-ISP2`/gateway.
3. Vigilar convergencia del 50/50 (el conteo de conexiones converge más lento que el
   tráfico; normal — ver memoria 26-may). Al cierre ya iba ISP1 96 / ISP3 96 Mbps.
4. Riesgo histórico: ISP3 (Telmex 8688225875) es el que flapea; si cae, el failover de
   ruta lo saca solo.
