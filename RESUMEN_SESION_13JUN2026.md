# Resumen de sesión — 13 de junio de 2026 (Post-cutover CCR2004: ajustes de red)

> Continuación del cutover CCR2004 del 12-jun. Hoy: cerrar pendientes + rediseño de egress.

## 1. ether7 desconectado + FIX DHCP de oficina (hueco del cutover)
- Enrique desconectó el cable de **ether7** del Balanceador (idle, sin IP) → sin efecto, todo OK.
- ⚠️ **Hallazgo:** el DHCP del segmento oficina `192.168.3.x` vivía en el **Balanceador** (`serverLAN` en ether7) — se omitió en el cutover. Al desconectar ether7 se cortó.
- **Replicado idéntico en CCR2004 ether2:** pool `poolLAN` `192.168.3.50-200`, gw `.254`, DNS `8.8.8.8/8.8.4.4`, lease 1d, **+ 11 reservas estáticas** (impresora HP `.92`, AP wifi `.97`, Servidor Securithor `.91`, laptops, etc.). `serverLAN` del Balanceador deshabilitado. Verificado repartiendo.
- Actualicé `ccr2004_stage_cold.rsc` con el bloque DHCP (commit `7211b63`).

## 2. Firewall CCR2004 ENDURECIDO + usuario sentinela
- Usuario Winbox **`sentinela` / `Sent1nel`** (grupo full) creado y probado.
- **Firewall input:** gestión (ssh22/winbox8291/api8728/8729) **solo desde address-list `mgmt_admin`** = `192.168.3.2` (server), `192.168.3.10` (PC Enrique), `172.19.0.0/16` (WSL) + trunk. Las PCs comunes de oficina ya NO pueden gestionar el router. ICMP input solo LAN (no WAN). `drop invalid` agregado. L2TP server deshabilitado. DHCP oficina preservado. Sin lockout (verificado posición antes de quitar reglas viejas).
- **Aclaración Winbox:** routers que ya no están en el L2 del PC (Balanceador `192.168.10.254`, CCRsentinela `192.168.10.50`) → conectar **por IP, no por vecino/MAC** (MNDP no cruza el router). El CCR2004 `192.168.3.254` sí aparece como vecino.

## 3. ⭐ REDISEÑO EGRESS: oficina por WISP, solo Odoo por Empresarial
**Directiva Enrique:** el Empresarial `.98` es exclusivo de Odoo; el resto del segmento `192.168.3.x` sale/entra por el Balanceador (WISP), como antes del cutover. El cutover había aislado de más (toda la oficina por `.98`), rompiendo MASadmin y las receptoras (asimetría: entraban por WISP, respondían por `.98`).

**Implementado con policy routing:**
- **CCR2004:** mangle prerouting — accept `src=.2 dst=!internos` (Odoo→default .98) + mark-routing `src=192.168.3.0/24 dst=!internos → to_wisp`; tabla ROS7 `to_wisp` (fib) + ruta `0.0.0.0/0 → 192.168.20.2 (trunk)`.
- **Balanceador:** mangle `in=ether6_WAN src=192.168.3.0/24 dst=!internos → mark-routing to_ISP1` (pineo oficina→ISP1).
- **Nota:** el WISP hoy es efectivamente ISP1 (ISP2 disabled, ISP3 failover) → expandible a PCC completo cuando regresen.

**Verificado:**
- Oficina: **272 conexiones established** a internet, egress `192.168.1.50` (ISP1). Navega bien (confirmado Enrique).
- Odoo (`.2`): sigue egress `.98` + interno OK.
- **MASadmin: abre desde fuera otra vez** (confirmado Enrique) — `.1` ahora simétrico en ISP1 → su DDNS del proveedor resincronizó.
- Securithor: paneles `established`.
- Interno (CCRsentinela/Monclova): OK.

**Causa de fondo aclarada:** la regla `:80 → .1` (MASadmin) está en el BALANCEADOR (`in=ether1_WAN/ISP1`), NO en el CCR2004 — correcto, MASadmin vive en WAN1/ISP1. NO se requiere recablear ether7 (todo va por el trunk ether6).

## 4. Estado del NAT del Balanceador (qué cambió)
- **Receptoras dst-nat (MASadmin/Securithor/NVR):** intactas, como original.
- **Deshabilitado (no borrado):** 11 reglas NAT `.98`/FFW + 3 pineos viejos (`in=ether7`) → movidos al CCR2004 / ether7 ya no existe.
- **Nuevo:** trunk ether6, pineo oficina (`in=ether6→ISP1`), ruta retorno, masquerade receptoras (parche simetría), address-lists `internos`/`receptores`.
- **Decisión:** dejar lo deshabilitado APAGADO un tiempo como rollback; borrar definitivo cuando lleve días estable.

## Pendientes para la próxima
1. Cuando ISP2/ISP3 del WISP estén OK → expandir el egress de oficina de pineo-ISP1 a **PCC completo** (ajuste menor en el Balanceador).
2. Cuando el cutover lleve días estable → **borrar definitivo** las 11 reglas `.98`/FFW + 3 pineos deshabilitados en el Balanceador (config 100% limpio).
3. Agregar el bloque DHCP al `ccr2004_stage_cold.rsc` — HECHO (commit 7211b63).
4. (Pendientes previos siguen) Monclova: nombres reales a los 4 cortesía + sync_active; FFW cambiar cable Wave `.4` (100M→1000M).

## Sin validar / notas
- El egress de oficina por ISP1 suma su carga a ISP1 (que ya lleva el WISP de clientes) — era así antes del cutover también. Vigilar si satura.
- Los parches de receptoras (masquerade dst=receptores + forward CCR2004) se quedan (complementarios, aseguran el inbound) aunque con el nuevo routing podrían ser redundantes — no se removieron para no arriesgar el inbound que funciona.
