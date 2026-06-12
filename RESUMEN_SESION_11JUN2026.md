# Resumen de sesión — 11 de junio de 2026

Jornada dedicada por completo a **red/infraestructura**: llegada del CCR2004, su aseguramiento, el diseño del cutover, y el análisis a fondo de la arquitectura de la planta WISP (que reveló topología no documentada).

---

## 1. CCR2004 nuevo — llegó y quedó asegurado
- **Equipo:** MikroTik CCR2004-16G-2S+, serial `HKF0AMHYZST`, ROS 7.19.5 stable (firmware al día). MAC `04:F4:1C:D9:4D:B5`.
- **Ubicación:** llegó casi de fábrica (config mínima, **sin DHCP server** → no era amenaza en la red de prod). Estaba cableado por `ether2` a la LAN de servidores `192.168.3.0/24`, sin IPv4 (solo IPv6-LL). Se ubicó por MNDP desde el Balanceador.
- **Acceso:** túnel SSH por el server (`-L 18729:192.168.3.249:8728` → API). El Balanceador filtra ese segmento desde WSL.
- **Aseguramiento aplicado (reversible, equipo en frío sin WANs):**
  - identity `CCR2004-STAGING`; IP mgmt `192.168.3.249/24` en ether2.
  - usuario `gemini_api`/`gemini_api2113` + password a `admin` (mismo esquema que Balanceador/CCRsentinela).
  - cerrados telnet/ftp/www/btest/discovery; quedan ssh/winbox/api/api-ssl.
  - backup de fábrica `factory_pre_claude`.
  - **Verificado** persistente tras caída de túneles (identity, IP, servicios, usuarios OK).

## 2. Decisiones de diseño del cutover (Enrique)
- **CCR2004 = gateway del /24 de servidores** (aislar): mover el uplink del switch de servidores del Balanceador (ether7) al CCR2004.
- **Trunk inter-router = cobre 1G** (los SFP+ del CCR2004 quedan reservados; **el CCR1009 no tiene SFP+**, es `7G-1C`).
- **Server confirmado 1G** (1 sola NIC `eno2` Intel I219-V; **no hay 10G posible**) → cae el supuesto original de "server por SFP+ 10G".
- CCR2004 hereda `192.168.3.254` (gateway actual) y conserva la IP pública `.98` → cutover transparente, los GPS no se reprograman.
- **FFW se migra junto con el server**: el bloque `187.251.199.96/29` (.98 server + .99 FFW) lo entrega TotalPlay por un solo handoff, no se parte.

## 3. Análisis de arquitectura — topología real descubierta
Auditados Balanceador (CCR1009-7G-1C, ROS 6.49.17) y CCRsentinela (CCR1016-12G, ROS 6.49.8), y entrada a los switches de planta:
- **No hay VLANs en NINGÚN lado** (ni routers ni switches): toda la planta de gestión+antenas `10.10.10.0/24` es **un L2 plano**.
- El "switch administrado" resultó ser un **Planet GSW-2401** (24p, **no administrado**, sin IP) como nodo central del site; a él van solo 4 cables: CCRsentinela `ether5`, 2 EdgeSwitch, UISP.
- Los "EdgeSwitch" son **EdgeSwitch 8XP PoE PRO** con firmware airOS/TOUGHSwitch (shell BusyBox, NO CLI Cisco; config en `/tmp/system.cfg`). Confirmado `.59` con solo VLAN1 untagged. Credenciales `sentinela`/`SentinelaW1sp.`
- Mapa físico: site (2 EdgeSwitch `.59/.60`, sectoriales `.5-.8`, PBE `.50`, NVR `.4`, UISP `.11`, FFW Wave `10.99.99.3/.4`, 2 Mimosas→Cd Industrial); radio bases con EdgeSwitch: `.61` Cd Industrial, `.62` Parker, `.63` Rusias, `.65` Quinta Real.

## 4. Documentos generados
- **`CUTOVER_CCR2004_11JUN2026.md`** — runbook del servidor/Empresarial: mapeo de puertos, inventario auditado de dst-nat/FFW/VPN Monclova a migrar, script en frío, checklist de ventana, rollback.
- **`ARQUITECTURA_RED_SENTINELA_11JUN2026.pdf`** — antes/después/beneficios. **Enviado a Telegram.**
- **`ANEXO_RETIRO_PLANET_11JUN2026.md` + `.pdf`** — retirar el Planet, reemplazándolo por un `bridge-gestion` en el CCRsentinela (hw-offload + RSTP), checklist y rollback. **PDF enviado a Telegram.**

## 5. Memoria actualizada
- `project_ccr2004_separacion_servidor.md` — llegada, aseguramiento, decisiones, punteros a docs.
- `reference_topologia_fisica_planta_wisp.md` (NUEVO) — topología física, EdgeSwitch/Planet, hallazgo "no VLANs".
- `reference_credentials_index.md` — CCR2004 (§3), EdgeSwitch (§4c nuevo).
- `MEMORY.md` — punteros actualizados.

---

## Pendientes para la próxima sesión
1. **Confirmar dato físico del cutover CCR2004:** ¿el modem TotalPlay Empresarial y las antenas FFW van por cable directo al Balanceador (ether4/ether5) o pasan por algún switch? Es lo único que falta para cerrar el runbook al 100%.
2. **Agendar ventana de madrugada** para el cutover del CCR2004 (el server pierde red unos minutos al recablear). Luego: aplicar §4 del runbook en frío y ejecutar el checklist.
3. **Retiro del Planet** (anexo): ventana SEPARADA. En sitio: validar el trío de puertos con switch-chip común para el offload, y revisar reglas que citen `ether5 Lan1`.
4. **Confirmar EdgeSwitch `.60`** (hoy tenía SSH cerrado): validar por web que también es L2 plano (muy probable).

## Notas
- Nada se desplegó a producción: el CCR2004 solo recibió aseguramiento base (sin config WAN). Los demás routers solo se auditaron (lectura). Sin riesgo abierto.
- Backup de fábrica del CCR2004 guardado (`factory_pre_claude`).
