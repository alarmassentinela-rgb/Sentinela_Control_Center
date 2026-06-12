# Cutover CCR2004 — separar Servidor/Empresarial del WISP

**Fecha doc:** 11-jun-2026 · **Equipo:** MikroTik CCR2004-16G-2S+ serial `HKF0AMHYZST`, ROS 7.19.5 stable
**Decisión base:** [[project-ccr2004-separacion-servidor]] · **Arquitectura WISP origen:** [[reference-balanceador-pcc-arquitectura]]

> El CCR2004 pasará a ser **el router de Empresarial + segmento de servidores + FFW + VPN Monclova**. El CCR1009 (Balanceador) queda como **WISP puro**. Esto elimina la causa raíz del bug de egress del 9-jun (servidor y WISP compartían el ruleset PCC).

---

## 0. Estado actual del CCR2004 (ya hecho por Claude, 11-jun)
- Llegó casi de fábrica (config mínima: solo `192.168.88.1/24` huérfana en ether15, **sin DHCP/bridge/firewall** → no era amenaza en la LAN de prod).
- **Cableado por ether2** a la LAN de servidores (L2 con el server, sin IPv4 propia hasta ahora).
- **Asegurado:** identity `CCR2004-STAGING`, IP mgmt `192.168.3.249/24` en ether2, user `gemini_api`/`gemini_api2113` + password a `admin`, cerrados telnet/ftp/www/btest/discovery (quedan ssh/winbox/api/api-ssl). Backup de fábrica `factory_pre_claude.backup`.
- **Acceso:** túnel SSH por el server → `ssh -p 2222 -i ~/.ssh/id_rsa_sentinela -N -L '18729:192.168.3.249:8728' egarza@192.168.3.2` → API a `127.0.0.1:18729`.

---

## 1. Decisiones tomadas (Enrique, 11-jun)
1. **CCR2004 = gateway del /24 de servidores** (aislar de verdad). El uplink del switch de servidores se mueve del balanceador (ether7) a un puerto del CCR2004.
2. **Trunk inter-router = cobre 1G** (no SFP+ por ahora). Los 2× SFP+ quedan reservados para futuro 10G.
3. Server confirmado **1 sola NIC 1G** (`eno2`, Intel I219-V). No hay 10G posible en el server con este hardware.

---

## 2. Mapeo de puertos propuesto del CCR2004  ⚠️ (Enrique cablear conforme a esto)
| Puerto CCR2004 | Rol | Direccionamiento | Va físicamente a |
|---|---|---|---|
| **ether1** | WAN Empresarial | `192.168.100.2/24` (modem) + `187.251.199.98/29` + `187.251.199.99/29`, gw `187.251.199.97` | cable handoff TotalPlay (modem/ONT) |
| **ether2** | LAN Servidores | `192.168.3.254/24` (hereda el gateway actual) — hoy `.249` mgmt | switch del segmento de servidores |
| **ether3** | FFW radio bridge | `10.99.99.1/29` | antenas Wave FFW (cable que hoy va al balanceador ether5) |
| **ether4** | Trunk a CCR1009 | `192.168.20.1/30` | puerto libre del CCR1009 (cobre) |
| sfp-sfpplus1/2 | reservado 10G | — | — |

**Por qué `.254` y no `.1`:** todos los hosts del /24 (incluido el server) usan **`192.168.3.254`** como gateway (es el balanceador ether7 hoy, MAC `c4:ad:34:de:15:59`). Si el CCR2004 hereda `.254`, **ningún host se reconfigura**. (El `.1` es otro equipo —MASadmin viejo—, no tocar.)

**FFW se migra sí o sí en el mismo cutover:** el bloque público `187.251.199.96/29` (que incluye `.98` server y `.99` FFW) lo entrega TotalPlay por **un solo handoff**. Si el handoff pasa al CCR2004, `.99`/FFW debe vivir también en el CCR2004 — no se puede partir el /29 entre dos routers.

---

## 3. Inventario a migrar (auditado del Balanceador 11-jun) — NO perder nada

### 3a. dst-nat entrantes sobre `187.251.199.98` → server `192.168.3.2`
| Puerto | Destino | Nota |
|---|---|---|
| tcp 8070 | .2:8070 | Odoo 18 |
| tcp 80 / 443 | .2:80 / :443 | HTTP/HTTPS (NPM) |
| tcp+udp 10001 | .2:10001 | Receptor de alarmas |
| tcp 5678 | .2:5678 | n8n |
| tcp 8443 | 10.10.10.11:8443 | UISP Console (vía trunk) |
| tcp 2222 | .2:2222 | SSH — **solo src `31.220.58.17` (Irving)** |
| tcp+udp 5001-5150 | .2 | SentiCar/Traccar GPS |

### 3b. FFW (`187.251.199.99` ↔ `10.99.99.2`)
- 1:1 NAT IN: `.99` → `10.99.99.2`; OUT src-nat: `10.99.99.2` → `.99`.
- mangle: forzar salida por `.99` (en CCR2004 es nativo, sin PCC) + **MSS clamp 1452** in/out en el bridge FFW.
- Gestión antenas (hoy entran por `192.168.3.254` del balanceador): 8083/4433→`10.99.99.3`, 8084/4434→`10.99.99.4`. En el CCR2004 el server las alcanza **directo** por ether3 (mismo router) — los dst-nat de gestión se pueden simplificar.

### 3c. VPN Monclova (L2TP/IPsec) — endpoint = `.98`
- l2tp-server: enabled, use-ipsec, auth mschap2, profile `default-encryption`.
- ppp secret `monclova_site`: local `172.16.50.2`, remote `172.16.50.1`.
- IPsec PSK: `Sx$i%9chXAjtuDwTUdyoqupNF0#k`.
- ⚠️ **Verificar a qué apunta el router de Monclova**: si usa el DDNS del balanceador (`e31e0dbb0e91.sn.mynetname.net`) hay que repuntarlo a `.98` fija o al nuevo DDNS del CCR2004. Si ya apunta a `.98` directo, no cambia nada.

### 3d. Pineo del server en el balanceador (desaparece)
- address-list `Servidores Wan4 = {192.168.3.2}` + mangle `PCCv2:odoo-salida-ISP4`. En el CCR2004 el server sale por `.98` nativamente — **ya no hace falta PCC** (esto es justo lo que se quería eliminar).

---

## 4. Script de configuración del CCR2004 (aplicar PRE-VENTANA, en frío)
> Seguro de cargar con los cables WAN desconectados: sin tráfico no afecta nada. **NO** poner `192.168.3.254` todavía (colisiona con el balanceador vivo) — eso va en la ventana (§5).

```rsc
# --- Identidad y NTP ---
/system identity set name=CCR2004-SERVIDOR
/system ntp client set enabled=yes
/system ntp client servers add address=pool.ntp.org

# --- Direcciones WAN/LAN/FFW/Trunk (ether2 .254 se pone en la ventana) ---
/ip address add address=192.168.100.2/24 interface=ether1 comment="WAN TotalPlay Empresarial (modem)"
/ip address add address=187.251.199.98/29 interface=ether1 comment="IP publica server .98"
/ip address add address=187.251.199.99/29 interface=ether1 comment="IP publica FFW .99"
/ip address add address=10.99.99.1/29 interface=ether3 comment="FFW radio bridge"
/ip address add address=192.168.20.1/30 interface=ether4 comment="Trunk a CCR1009 WISP"

# --- Rutas ---
/ip route add dst-address=0.0.0.0/0 gateway=187.251.199.97 comment="Default Empresarial"
/ip route add dst-address=192.168.10.0/24 gateway=192.168.20.2 comment="MGMT/WISP via trunk (CCR1009 .254, CCRsentinela .50)"
/ip route add dst-address=10.10.10.0/24 gateway=192.168.20.2 comment="UISP Console via trunk"

# --- NAT salida ---
/ip firewall nat add chain=srcnat out-interface=ether1 action=masquerade comment="Salida server por .98"
/ip firewall nat add chain=srcnat src-address=10.99.99.2 action=src-nat to-addresses=187.251.199.99 comment="FFW 1:1 OUT"
/ip firewall nat add chain=dstnat dst-address=187.251.199.99 action=dst-nat to-addresses=10.99.99.2 comment="FFW 1:1 IN"

# --- dst-nat entrantes al server (.98) ---
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=tcp dst-port=8070 action=dst-nat to-addresses=192.168.3.2 to-ports=8070 comment="Odoo"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=tcp dst-port=80  action=dst-nat to-addresses=192.168.3.2 to-ports=80  comment="HTTP"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=tcp dst-port=443 action=dst-nat to-addresses=192.168.3.2 to-ports=443 comment="HTTPS"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=tcp dst-port=10001 action=dst-nat to-addresses=192.168.3.2 to-ports=10001 comment="Alarmas TCP"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=udp dst-port=10001 action=dst-nat to-addresses=192.168.3.2 to-ports=10001 comment="Alarmas UDP"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=tcp dst-port=5678 action=dst-nat to-addresses=192.168.3.2 to-ports=5678 comment="n8n"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=tcp dst-port=8443 action=dst-nat to-addresses=10.10.10.11 to-ports=8443 comment="UISP Console"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=tcp dst-port=2222 src-address=31.220.58.17 action=dst-nat to-addresses=192.168.3.2 to-ports=2222 comment="SSH Irving"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=tcp dst-port=5001-5150 action=dst-nat to-addresses=192.168.3.2 comment="Traccar GPS TCP"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=udp dst-port=5001-5150 action=dst-nat to-addresses=192.168.3.2 comment="Traccar GPS UDP"

# --- MSS clamp FFW ---
/ip firewall mangle add chain=forward in-interface=ether3 action=change-mss new-mss=1452 tcp-flags=syn protocol=tcp comment="MSS FFW in"
/ip firewall mangle add chain=forward out-interface=ether3 action=change-mss new-mss=1452 tcp-flags=syn protocol=tcp comment="MSS FFW out"

# --- VPN Monclova (L2TP/IPsec) ---
/ip pool add name=vpn-monclova ranges=172.16.50.1
/ppp profile add name=monclova local-address=172.16.50.2 remote-address=172.16.50.1
/ppp secret add name=monclova_site service=l2tp profile=monclova password="<ver reference_vpn_monclova / credentials_index §3a>"
/interface l2tp-server server set enabled=yes use-ipsec=yes ipsec-secret="Sx\$i%9chXAjtuDwTUdyoqupNF0#k" authentication=mschap2 default-profile=monclova

# --- Firewall (protección del router) ---
/ip firewall filter add chain=input connection-state=established,related action=accept
/ip firewall filter add chain=input protocol=icmp action=accept
/ip firewall filter add chain=input src-address=192.168.3.0/24 action=accept comment="MGMT desde LAN servidores"
/ip firewall filter add chain=input src-address=192.168.20.0/30 action=accept comment="MGMT desde trunk"
/ip firewall filter add chain=input action=drop comment="drop resto input"
/ip firewall filter add chain=forward connection-state=established,related action=accept
/ip firewall filter add chain=forward connection-state=invalid action=drop
/ip firewall filter add chain=forward connection-nat-state=dstnat action=accept comment="permitir entrantes dst-nat"
/ip firewall filter add chain=forward src-address=192.168.3.0/24 action=accept comment="LAN servidores → todo"
/ip firewall filter add chain=forward in-interface=ether3 action=accept comment="FFW"
/ip firewall filter add chain=forward action=drop comment="drop resto forward"
```

---

## 5. Checklist de cutover (VENTANA de madrugada — Enrique en sitio, Claude por túnel)
**Downtime esperado:** unos minutos (mientras se recablea y se conmutan IPs).

**Preparación (antes de la ventana):**
- [ ] Aplicar §4 al CCR2004 (en frío). Verificar que NO rompe nada (sin cables WAN no enruta).
- [ ] Backup del Balanceador: `/export file=ccr1009_pre_cutover` + dump del NAT/mangle.
- [ ] Confirmar a qué apunta el peer de Monclova (§3c).
- [ ] Tener a la mano cable de trunk (cobre) y patch del switch de servidores.

**Ventana — orden:**
1. [ ] **Balanceador:** *deshabilitar* (NO borrar) lo de Empresarial para permitir rollback: dst-nat `.98`, FFW (mangle/NAT/MSS), VPN Monclova, pineo `Servidores Wan4`. Quitar/deshabilitar las IPs `.98/.99/100.2` de ether4 y `10.99.99.1` de ether5.
2. [ ] **Físico:** handoff TotalPlay → CCR2004 **ether1**. Antenas FFW → CCR2004 **ether3**. Trunk cobre CCR2004 **ether4** ↔ CCR1009 (puerto libre, ponerle `192.168.20.2/30`). Uplink switch servidores: balanceador ether7 → CCR2004 **ether2**.
3. [ ] **CCR2004:** `/ip address set [find interface=ether2] address=192.168.3.254/24` (de `.249` a `.254`). Habilitar ether1.
4. [ ] **CCR1009 (WISP):** agregar ruta de retorno `192.168.3.0/24 gateway=192.168.20.1` (y `10.10.10.0/24` / UISP si aplica). Quitar IP `192.168.3.254` de ether7 (ya no es gateway del /24).
5. [ ] **Verificar** (§6).

---

## 6. Verificación post-cutover
- [ ] Server sale a internet con IP pública correcta: `curl ifconfig.me` desde `192.168.3.2` → `187.251.199.98`.
- [ ] Entrantes al server: Odoo (`https://...:8070`/443), n8n, **receptor de alarmas 10001** (crítico), **Traccar GPS 5001-5150** (un N01K reporta), SSH Irving 2222.
- [ ] **FFW arriba:** ping `10.99.99.3`/`.4`, tráfico de la maquiladora fluye, IP pública FFW `.99` OK.
- [ ] **VPN Monclova** reconecta (`/ppp active` muestra `monclova_site`).
- [ ] Server llega a CCRs por trunk: ping `192.168.10.254`, `192.168.10.50`, UISP `10.10.10.11`. (Para netwatch, Odoo→CCRsentinela, reconciliación.)
- [ ] WISP intacto (no se tocó el PCC del CCR1009).
- [ ] DDNS/Cloudflare: `radar.senticar.com` y demás siguen por Cloudflare Tunnel (saliente, no depende de dst-nat) — confirmar túnel arriba.

---

## 7. Rollback (rápido, porque en el balanceador solo se DESHABILITÓ, no se borró)
1. Recablear: handoff → balanceador ether4, FFW → ether5, switch servidores → balanceador ether7.
2. Balanceador: re-habilitar las reglas/IPs deshabilitadas en el paso 1 de §5; restaurar `192.168.3.254` en ether7.
3. CCR2004: deshabilitar ether1, volver ether2 a `.249`.
4. Verificar server con `curl ifconfig.me`.

---

## 8. Pendientes / a confirmar con Enrique antes de la ventana
- **¿Cuándo es la ventana?** (madrugada; avisar para tener el túnel listo).
- **Modem TotalPlay:** confirmar que el handoff entrega el `/29` con gateway `.97` en el mismo cable (la ruta default del balanceador usa `187.251.199.97`, y `192.168.100.2/24` es la red de gestión del modem). Si el modem exige estar en `192.168.100.x` para enrutar el público, se mantiene esa IP (ya está en §4).
- **DDNS del CCR2004:** habilitar `/ip cloud` propio y decidir si Monclova apunta a `.98` fija (recomendado) o al nuevo DDNS.
- **Camino de egress de respaldo del server** (plan original): hoy no hay. Con el trunk al CCR1009 se podría dar al server salida de respaldo por WISP si TotalPlay Empresarial cae (ruta default secundaria de mayor distancia via `192.168.20.2`). Decidir si se incluye.
