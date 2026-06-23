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

**El 3-way se REVIRTIÓ a los pocos minutos** — llegaron alertas de "caída" del
CCRsentinela (monitorea `1.1.1.1`): ~1/3 de sus pings de keepalive salían por TotalPlay,
y el **jitter de TotalPlay** (la sonda `to_ISP2 principal` flapea) los hacía fallar
intermitente → falsas caídas (y probables blips reales a clientes que caían en ISP2).
**Revertido a `foIsps={{1;1};{3;1}}` (50/50 ISP1+ISP3); las alertas pararon de inmediato.**

**LECCIÓN:** TotalPlay NO sirve para balance activo por su jitter; queda como **failover
de último recurso (dist-3)**. Confirma el diseño original (TotalPlay = emergencia).

**Estado final del Balanceador (cierre real de la sesión):**
- **Balanceo 50/50 ISP1+ISP3** (ambos Telmex) — clasificador arriba de `*14`.
- **ISP2/TotalPlay = failover dist-3** (DHCP `192.168.100.4`, MSS clamp 1440, probe
  activo). Cero tráfico/monitoreo por ISP2 en operación normal → sin alertas. Solo entra
  si caen los DOS Telmex.
- `foIsps=foIspsAnt=1;1;3;1`. Todo persistente.
- Todo el trabajo de ISP2 (subred, DHCP, MSS clamp, dist-3) sigue válido y deja el
  failover listo y funcional.

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

---

# Parte 4 — Usuarios del equipo + página de rastreo SentiCar (FSM)

(Sesión vespertina, independiente del trabajo de red de arriba.)

## Alta de usuarios del equipo operativo (prod `Sentinela_V18`)
Se dieron de alta / ajustaron **7 usuarios** vía XML-RPC. Credenciales entregadas por
PDF a Telegram (no se guardan en repo ni memoria). Detalle de roles en memoria
`project_usuarios_equipo_fsm_central.md`.

| Persona | Login | Rol | Notas |
|---|---|---|---|
| Mirna Barbosa | `central@sentinela.com.mx` | Despacho FSM + tablero (`group_fsm_dispatcher`) | id 8: era portal "PRUEBAS SENTINELA", **convertido a interno** (quitar `base.group_portal`, agregar interno+dispatcher) |
| Kevin Rivera | `kevin.rivera` | Despacho FSM + tablero | nuevo (id 15) |
| Juan José Hernández | `juan.jose.hernandez` | Despacho FSM + tablero | nuevo (id 16) |
| Jesús González | `jgonzalez@sentinela.com.mx` | Técnico (`group_fsm_user`) | ya existía; password reseteado |
| Juan Padilla | `jpadilla@sentinela.com.mx` | Técnico | ya existía SIN grupo → se agregó `group_fsm_user` |
| Manuel Sandoval | `manuel.sandoval` | Patrullero | ya existía; unidad **March** (unit id 1) |
| Diego Banda Cruz | `diego.banda` | Patrullero | nuevo (id 14), `is_patrol=True`, unidad **Rapid** (unit id 3) |

- **Trampa confirmada:** el campo `default_patrol_unit_id` solo aparece en el form si
  `is_patrol=True` (`res_users_views.xml`: `invisible="not is_patrol"`).
- **Login NO tiene que ser correo** (Manuel/Diego/Kevin/Juan José usan usuario simple).
- **Unidades:** Rapid (id 3) NO es vehículo exclusivo de patrulla — habitual de Diego pero
  compartible para despachos puntuales. La unidad por defecto se cambia en el form o al despachar.
- Verificación: los 7 logins autenticaron por XML-RPC (`AUTH_OK=True`).

## Entregables a Telegram (bot interno @Sentinela2026_bot, chat Enrique 7965190381)
- **PDF `Usuarios_Sentinela_Odoo.pdf`** (reportlab): credenciales + permisos por rol +
  guía paso a paso para agregar/quitar permisos desde Odoo. ⚠️ salió **sin logo**
  (pendiente: regenerar con logo por la regla `feedback_logo_documentos_sentinela`).
- **4 mensajes** listos para reenviar a cada técnico/patrullero con la liga de la app
  **Sentinela Tech** (`https://sentinela.mx/tech/dashboard`, PWA), su usuario, contraseña
  y pasos de instalación (Android/iPhone).

## Página de rastreo del cliente (`/SentiCar/rastreo/<token>`)
Plantilla `customer_tracking_map` en `sentinela_fsm/views/tech_portal_templates.xml`.
- **v18.0.1.11.2** (commit `be0033e`): ícono **SentiCar pwa-512** (copiado a
  `static/src/senticar_pwa_512.png`). Se agregó al `<head>` favicon + apple-touch-icon +
  **Open Graph** (`og:image` con URL absoluta vía `web.base.url`) → la **miniatura del
  enlace en el Telegram "técnico en camino"** ahora muestra el ícono SentiCar. También se
  reemplazó el logo interno (carrito viejo → ícono pwa-512, 64px redondeado).
- **v18.0.1.11.3** (commit `d3c2f32`): la celda **"Estatus"** dejaba puro branding
  ("SentiCar Security/Service by Sentinela"); ahora muestra **estatus real** según la orden:
  `🕒 Asignado` / `🚚 En camino` (servicio) / `🚓 En camino` (patrullaje) / `✅ En sitio`
  (cuando `arrival_date` está puesto). La publicidad ya la cubren el ícono + logo del pie.

Deploy verificado: STAGING limpio → PROD `V18`, ambas versiones cargadas, página real
renderizando el ícono (`og:image` presente) y el estatus (`🚓 En camino` en OS-00010).
Tags: `v18.0.1.11.2-sentinela_fsm`, `v18.0.1.11.3-sentinela_fsm`.
⚠️ Nota Telegram: cachea el preview por URL; los enlaces NUEVOS (cada orden = token nuevo)
ya saldrán con ícono; enlaces viejos ya mostrados pueden seguir cacheados un rato.

## Pendientes (parte 4)
1. **Regenerar el PDF de credenciales CON el logo** de Sentinela y reenviarlo (regla
   `feedback_logo_documentos_sentinela`). Quedó sin logo en el primer envío.
2. (Opcional) Disparar una orden de prueba para ver en vivo la miniatura del Telegram con el ícono.

---

# Parte 5 — Auto-suspensión por mora: crones de cobranza estaban apagados

## Investigación: ¿por qué SUB-0305 no se suspendió con 7 días de mora?
Disparador: Enrique preguntó por qué SUB-0305 seguía activa pese a >5 días de factura
vencida (política = suspender a los 5 días).

**Hallazgo:** la sub cumplía TODAS las condiciones de `_cron_auto_suspend_overdue`
(`subscription.py`): `state=active`, `billing_mode=normal`, `days_to_suspend=5`, sin
prórroga, factura `INV/2026/00090` `posted`/`not_paid` vencida 15-jun (residual $550).
Debió suspenderse el 20-jun. **No era la sub ni la lógica.**

**Causa raíz:** los 4 crones de cobranza quedaron `active=False` desde el **26-may**
(`lastcall 2026-05-26`, se apagaron para el arranque de facturación) y **nunca se
reencendieron** → todo junio sin enforcement: cero auto-suspensiones, cero recordatorios.

## Acción: reactivar los crones de cobranza (NO los de timbrado)
A petición de Enrique ("activa los crones, solo el que timbra las facturas no"):
- Reactivados vía `odoo shell` en prod (api_user NO puede escribir `ir.cron`; XML-RPC de
  egarza no autentica → `docker exec -i odoo18-migration-web-1 odoo shell -d Sentinela_V18`):
  - **55** Auto-Suspender por Facturas Vencidas
  - **56** Enviar Recordatorios de Cobranza
  - **40** Revisar Prórrogas Vencidas
  - **57** Revisar Fin de Leasing
- **NO se tocaron** los de generación/timbrado (39 Pre-Facturas, 31 recurrentes, 34).

## Resultado verificado
- El `nextcall` quedó en el pasado → el cron 55 disparó en el siguiente barrido
  (`lastcall 2026-06-23 00:11:47`) y **suspendió 20 suscripciones**.
- **Verificado 20/20** en estado `suspension` / `technical_state=suspended`.
- **Alcance real = solo INTERNET** (corta PPPoE/walled-garden en CCRsentinela). Alarmas
  no provisiona en prod (monitoring en desarrollo) y GPS no tiene SIMs ligadas a cuentas
  → no corta ningún SIM/GPS. (Confirmado por Enrique.)
- Lista de las 20 enviada al Telegram de Enrique (bot facturación `8373567654`).

Suscripciones suspendidas: SUB-0117, 0158, 0185, 0199, 0200, 0201, 0211, 0225, 0226,
0229, 0230, 0231, 0237, 0288, 0305, 0306, 0316, 0358, 0363, 0365.
(Víctor Manuel García ×4, Divisas Frontera Longoria ×4.)

## Memoria actualizada
- `project_subscriptions_arranque_facturacion.md` — nueva sección "Crones de cobranza
  apagados todo el 1er ciclo — REACTIVADOS 22-jun-2026" (causa raíz + cómo se reactivó +
  alcance real).

## Pendientes (parte 5)
1. Vigilar que el cron 56 (recordatorios) no mande correos atrasados en masa de todo junio.
2. Revisar mañana si alguna de las 20 ya pagó para reactivación automática.
3. Confirmar que ninguna de las 20 era cliente que debiera ir en prórroga/cortesía.
