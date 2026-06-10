---
name: diagnostico-red
description: >-
  Diagnostica problemas de red multi-WAN del Balanceador: "el server no sale a
  internet", "conecta pero los datos se cuelgan", lentitud WISP, una WAN
  degradada, o floLIVE/Odoo con timeout. Sigue el runbook real del CCR1009
  (asimetría routing/NAT, regla de oro passthrough=no, ping por WAN). Úsalo antes
  de tocar mangle/NAT/rutas — encapsula las trampas que ya rompieron producción.
---

# Diagnóstico de red — Balanceador multi-WAN

Infra crítica: el Balanceador (CCR1009, `192.168.10.254`) rutea TODO — clientes
WISP + servidores + FFW. Tocar mangle/NAT/rutas afecta a todos. **Respaldar antes
de cualquier cambio** (`/export` o dump JSON del mangle). Arquitectura completa en
la memoria `reference_balanceador_pcc_arquitectura`.

## Acceso
- API RouterOS `192.168.10.254`, user `gemini_api` / `gemini_api2113` (lib
  `routeros_api` en `claude-env`). Entro desde 192.168.10.254 (MGMT).
- Para diagnosticar WANs, hacer **ping desde el router a `208.67.222.222`**
  (OpenDNS) o `9.9.9.9` — **NO 8.8.8.8** (da falsos resultados en estas WANs).

## Mapa de WANs (verificar estado actual, puede cambiar)
| Iface | ISP | Estado típico |
|---|---|---|
| ether1_WAN | ISP1 (gw 192.168.1.254) | activa, casi todo el tráfico cae aquí |
| ether2_WAN | ISP2 TotalPlay Comercial | DISABLED (degradado) |
| ether3_WAN | ISP3 Telmex | failover (loss histórico) |
| ether4_WAN | ISP4 TotalPlay Empresarial (.98) | WAN del SERVER y FFW |
| ether5_WAN | FFW radio (maquiladora) | NAT 1:1 a .99 |
| ether7_LAN | LAN servidores 192.168.3.0/24 | aquí cuelga Odoo .2 |

## Síntoma A — "conecta pero los datos se cuelgan" (asimetría routing/NAT)
El más traicionero: el handshake TCP conecta, pero TLS/datos hacen timeout
(`curl http=000`, `Read timed out`). Receta:

1. **En el host afectado** (ej. server): `ss -ti dst <ip>`. Si ves `bytes_acked:1`
   + `retrans:x/8` + `orig-bytes` subiendo sin `repl` = los datos salientes se
   pierden tras el handshake. (Descartar MTU: `ping -M do -s 1472`; DNS: `name=`
   bajo; no es el destino.)
2. **En el Balanceador:** `/ip firewall connection` filtrado por src/dst. Comparar
   **`connection-mark`** (qué WAN rutea) vs **`reply-dst-address`** (a qué IP pública
   NATeó). Si NO coinciden (ej. `ISP1_conn` + `reply-dst=.98 de ether4`) =
   **asimetría** → el SYN sale por una WAN, los datos por otra con IP ajena →
   upstream descarta (uRPF).
3. **Causa típica:** una regla de **pineo de servidor** con `passthrough=yes` se cuela
   al clasificador PCC y sella la conexión con otra WAN. **REGLA DE ORO: las reglas
   de pineo (`src-address-list="Servidores WanX" → routing-mark=to_ISPX`) DEBEN
   llevar `passthrough=no`.** Fue exactamente el bug del egress del server (9-jun):
   regla `*5E` (Servidores Wan4 = {192.168.3.2}) creada con el default `yes`. Fix:
   ```
   /ip firewall mangle set [find comment="PCCv2:odoo-salida-ISP4"] passthrough=no
   ```
   Verificar: `curl` al destino desde el server da `http=200`. Rollback: `passthrough=yes`.
4. Otras causas: host en 2 address-lists a la vez; tabla `to_ISPx` con default a WAN caída.

- **Pista lateral:** desde **WSL** el tráfico sale por su propio bypass
  (`172.19.0.0/16 via 192.168.3.10` = PC Enrique). Si WSL funciona y el server NO,
  el problema es el marcado/WAN del server, no DNS/MTU/destino.

## Síntoma B — lentitud WISP / una WAN degradada
- Ping por cada WAN a `208.67.222.222` (no 8.8.8.8) → medir loss/latencia por iface.
- Si una WAN tiene loss selectivo, **disabled** esa iface (histórico: ether3 Telmex
  con 13% loss e ether2 con loss selectivo Cloudflare → ambas disabled, tráfico subió).
- **El PCC de clientes WISP debe contener SOLO ether1, ether2, ether3.** WAN4
  (TotalPlay Empresarial) NUNCA va al PCC de WISP.
- Netwatch actual solo NOTIFICA (no mueve rutas automáticamente). Failover real
  depende de las rutas recursivas de `to_ISPx`.

## Blast radius — qué NO tocar sin pensar
- Cambiar el pineo del SERVER (Servidores Wan4) **NO** afecta a FFW (entra por ether5,
  reglas propias). Verificar igual: antenas `10.99.99.3/.4` responden.
- El PCC de clientes WISP es independiente del egress del server. No mezclar.
- Cualquier cambio al mangle/NAT del Balanceador = respaldo JSON antes + rollback escrito.

## Operativa Odoo desde el server (para validar internet desde Odoo)
```bash
ssh -p 2222 -i ~/.ssh/id_rsa_sentinela egarza@192.168.3.2 \
  'docker exec -i odoo18-migration-web-1 odoo shell -d Sentinela_V18 --no-http' < script.py
# en odoo shell hay que env.cr.commit() para persistir
```
Ej. de verificación end-to-end: `flolive_service._get_auth_token()` → `TOKEN_OK`.
