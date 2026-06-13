# =============================================================================
#  CCR2004-16G-2S+  ·  serial HKF0AMHYZST  ·  ROS 7.19.5
#  CONFIG EN FRÍO (pre-ventana) — separar Servidor/Empresarial/FFW/VPN del WISP
#  Doc base: CUTOVER_CCR2004_11JUN2026.md  ·  Memoria: project-ccr2004-separacion-servidor
# -----------------------------------------------------------------------------
#  CÓMO Y CUÁNDO APLICAR:
#   - Aplicar con los cables WAN (ether1 handoff TotalPlay y ether3 FFW)
#     DESCONECTADOS. Sin tráfico no enruta nada → no afecta producción.
#   - ether2 sigue en 192.168.3.249 (mgmt). NO se pone 192.168.3.254 aquí:
#     eso colisiona con el balanceador vivo. El .254 va EN LA VENTANA (§5 del doc).
#   - Importar con:  /import file-name=ccr2004_stage_cold.rsc
#     (subir el archivo al CCR2004 por el túnel SSH al .249 primero)
#   - Acceso: ssh -p 2222 -i ~/.ssh/id_rsa_sentinela -N \
#       -L 18729:192.168.3.249:8728 egarza@192.168.3.2  → API a 127.0.0.1:18729
#
#  CABLEADO OBJETIVO (confirmar antes de la ventana):
#     ether1 = handoff TotalPlay (modem/ONT)      [WAN Empresarial /29]
#     ether2 = switch Planet GSW-2401 LAN .3.x     [server + PCs oficina]
#     ether3 = antenas Wave FFW                    [FFW radio bridge]
#     ether4 = trunk cobre a CCR1009 ether7        [/30 router-a-router]
#     ¡OJO! El switch va a ether2, el trunk a ether4. No cruzarlos (doble gw/loop).
# =============================================================================

# --- Identidad y NTP (ROS7) ---
/system identity set name=CCR2004-SERVIDOR
/system ntp client set enabled=yes servers=pool.ntp.org

# --- Direcciones WAN / LAN / FFW / Trunk ---
# NOTA: ether2 .254 se aplica EN LA VENTANA, no aquí. Por ahora queda el .249 mgmt.
/ip address add address=192.168.100.2/24  interface=ether1 comment="WAN TotalPlay Empresarial (gestion modem)"
/ip address add address=187.251.199.98/29 interface=ether1 comment="IP publica server .98"
/ip address add address=187.251.199.99/29 interface=ether1 comment="IP publica FFW .99"
/ip address add address=10.99.99.1/29     interface=ether3 comment="FFW radio bridge"
/ip address add address=192.168.20.1/30   interface=ether4 comment="Trunk a CCR1009 (WISP)"

# --- Rutas ---
# Diseno: internet por .97; TODO lo privado (RFC1918) por el trunk -> balanceador,
# que es el hub de WISP/UISP/Monclova. Replica lo que hoy hace el server (default al .254).
# Las /24 locales (192.168.3.0/24 ether2, 192.168.20.0/30 ether4, FFW 10.99.99.0/29 ether3,
# 192.168.100.0/24 ether1) ganan por ser mas especificas que estos agregados.
/ip route add dst-address=0.0.0.0/0      gateway=187.251.199.97 comment="Default Empresarial TotalPlay"
/ip route add dst-address=10.0.0.0/8     gateway=192.168.20.2   comment="10.x interno (WISP/UISP/Monclova LANs/Argus) via trunk->balanceador"
/ip route add dst-address=172.16.0.0/12  gateway=192.168.20.2   comment="WISP clientes + tunel Monclova (172.16.50.1) + WSL via trunk"
/ip route add dst-address=192.168.0.0/16 gateway=192.168.20.2   comment="Resto LAN interna (balanceador 192.168.10.x, Monclova 30/50) via trunk"

# --- NAT salida ---
/ip firewall nat add chain=srcnat out-interface=ether1 action=masquerade comment="Salida server por .98"
/ip firewall nat add chain=srcnat src-address=10.99.99.2 action=src-nat to-addresses=187.251.199.99 comment="FFW 1:1 OUT (.99)"
/ip firewall nat add chain=dstnat dst-address=187.251.199.99 action=dst-nat to-addresses=10.99.99.2 comment="FFW 1:1 IN (.99 -> 10.99.99.2)"

# --- dst-nat entrantes al server sobre .98 ---
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=tcp dst-port=8070      action=dst-nat to-addresses=192.168.3.2 to-ports=8070  comment="Odoo 18"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=tcp dst-port=80        action=dst-nat to-addresses=192.168.3.2 to-ports=80    comment="HTTP (NPM)"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=tcp dst-port=443       action=dst-nat to-addresses=192.168.3.2 to-ports=443   comment="HTTPS (NPM)"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=tcp dst-port=10001     action=dst-nat to-addresses=192.168.3.2 to-ports=10001 comment="Receptor alarmas TCP"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=udp dst-port=10001     action=dst-nat to-addresses=192.168.3.2 to-ports=10001 comment="Receptor alarmas UDP"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=tcp dst-port=5678      action=dst-nat to-addresses=192.168.3.2 to-ports=5678  comment="n8n"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=tcp dst-port=8443      action=dst-nat to-addresses=10.10.10.11 to-ports=8443  comment="UISP Console (via trunk)"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=tcp dst-port=2222 src-address=31.220.58.17 action=dst-nat to-addresses=192.168.3.2 to-ports=2222 comment="SSH Irving (solo 31.220.58.17)"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=tcp dst-port=5001-5150 action=dst-nat to-addresses=192.168.3.2 comment="SentiCar/Traccar GPS TCP"
/ip firewall nat add chain=dstnat dst-address=187.251.199.98 protocol=udp dst-port=5001-5150 action=dst-nat to-addresses=192.168.3.2 comment="SentiCar/Traccar GPS UDP"

# --- MSS clamp FFW (1452) ---
/ip firewall mangle add chain=forward in-interface=ether3  protocol=tcp tcp-flags=syn action=change-mss new-mss=1452 comment="MSS FFW in"
/ip firewall mangle add chain=forward out-interface=ether3 protocol=tcp tcp-flags=syn action=change-mss new-mss=1452 comment="MSS FFW out"

# --- VPN Monclova: NO VA AQUI ---
# Verificado 12-jun: Monclova marca al DDNS del balanceador (mynetname -> 187.158.227.206,
# otra WAN tras NAT), NO a la .98. Es un SITIO WISP completo (PPPoE/Argus). Se queda en el
# CCR1009. NO migrar. NO levantar L2TP server aqui (evita doble endpoint con el mismo PSK).

# --- Firewall (proteccion del router) ---
/ip firewall filter add chain=input  connection-state=established,related action=accept
/ip firewall filter add chain=input  protocol=icmp action=accept
/ip firewall filter add chain=input  src-address=192.168.3.0/24  action=accept comment="MGMT desde LAN servidores"
/ip firewall filter add chain=input  src-address=192.168.20.0/30 action=accept comment="MGMT desde trunk"
/ip firewall filter add chain=input  action=drop comment="drop resto input"
/ip firewall filter add chain=forward connection-state=established,related action=accept
/ip firewall filter add chain=forward connection-state=invalid action=drop
/ip firewall filter add chain=forward connection-nat-state=dstnat action=accept comment="permitir entrantes dst-nat"
/ip firewall filter add chain=forward src-address=192.168.3.0/24 action=accept comment="LAN servidores -> todo"
/ip firewall filter add chain=forward in-interface=ether3 action=accept comment="FFW"
/ip firewall filter add chain=forward action=drop comment="drop resto forward"

# =============================================================================
#  PENDIENTE DE LA VENTANA (NO va en frío):
#    /ip address set [find interface=ether2] address=192.168.3.254/24   (de .249 a .254)
#    + habilitar ether1, recablear handoff/FFW/trunk/switch, deshabilitar lo del balanceador.
#  Ver §5 (checklist), §6 (verificacion), §7 (rollback) del doc.
# =============================================================================
