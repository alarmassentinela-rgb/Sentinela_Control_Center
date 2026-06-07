# Resumen de sesión — 7-jun-2026

Día largo. Foco principal: **balanceo PCC del Balanceador** (investigación a fondo + intentos en producción, todo revertido a estado seguro). También cierre de la puerta de Argus, falsa alarma de un cliente, y preparación del traspaso a la laptop para retomar en la madrugada.

---

## 1. 🔴 PCC del Balanceador — EL TEMA GRANDE (sin cerrar, clientes seguros)

### Estado al cerrar
- **TODOS los clientes WISP en ether1 (Telmex ISP1), ~150-240 Mbps, funcionando.** `foIsps={{1;1}}`.
- **ether2 (TotalPlay) APAGADO. ether3 (Telmex ISP3) ENCENDIDO pero idle** (se dejó ON a propósito: da posible failover si ether1 cae — la ruta to_ISP1 tiene dist2 a ether3).
- Reglas NAT por interfaz ether2/ether3 quedaron puestas (correctas, inofensivas).

### Lo que se descubrió
1. **El PCC estaba APAGADO** (deshabilitado a mano por `admin` tras el rediseño 26-may) → todo el WISP salía por un solo ISP. La causa: Enrique apagó ether2/ether3 por inestables, reactivó solo ether3 pero el balanceo nunca se reactivó.
2. **El control del PCC es el script `failoverConfig` (`foIsps={{id;peso}}`)**, NO editar reglas mangle a mano (un scheduler las reescribe cada 10s). Mapa WAN: ether1=Telmex, ether2=TotalPlay, ether3=Telmex (estos 3 = WISP); ether4/5=Empresarial IP fija/FFW; ether6=libre; ether7=oficina.
3. **La infraestructura SÍ sirve** — probado en vivo con la PC de oficina **192.168.3.90**: ruteada a ether2 y ether3 (con flush de su conntrack) navegó perfecto, NAT correcto, descargas completas. **Sin afectar a un solo cliente.**
4. **Bug de NAT (arreglado):** el masquerade catch-all le ponía la IP de ether1 a todo → se agregaron reglas masquerade por interfaz (ether2/ether3).
5. **EL MURO (pendiente):** al aplicar el balance a los clientes (foIsps 2:1:2 + flush), las conexiones WISP **se marcan bien** (ISP1/ISP2/ISP3 en proporción correcta) **pero TODAS egresan ether1** (NAT 192.168.1.x; ether2/3 en 0). La **PC por ether7 con marca idéntica SÍ sale por ether3; el WISP por combo1 (src 192.168.10.50, NATeado por el CCR) NO.** Diferencia combo1 vs ether7 sutil, sin aislar.

### Pendiente madrugada
- Aislar por qué **combo1 ≠ ether7** (¿timing del 1er paquete? ¿algo del CCR-NAT?). 
- Comparar con el backup original de Argus (`pre_pcc_redesign.backup`, no legible por API) que SÍ balanceaba.
- **Probar el FAILOVER de verdad** (tirar ether1 unos segundos, ver si clientes brincan a ether3) — más importante que el balanceo.
- Detalle completo en `pcc_madrugada/HANDOFF_PCC_MADRUGADA.md` y memoria `project_pcc_redesign_26may2026.md`.

### Lecciones de tooling
- `re.sub(':global foIsps \\{.*?\\};')` non-greedy CORROMPE la línea → usar reemplazo de línea completa.
- Flush de conntrack por API es LENTO (~7000 conex) → background.
- Ping por API = falsos negativos. **Usar conntrack** (`reply-dst-address` = NAT-src, `repl-bytes` = vuelta).

---

## 2. 🔒 Argus — puerta cerrada al CCR (CCRsentinela)
Argus seguía conectado: el scheduler `argusblack_monitorinterfaz` revivía el túnel cada 2 min, y los usuarios full aceptaban login desde la red de Argus (10.231.71.0/24). **Cerrado** (sin tirar clientes, 101=101): (1) deshabilitado `argusblack_monitorinterfaz`; (2) deshabilitada interfaz `argusblack`; (3) quitado `10.231.71.0/24` de users sentinela/gemini_api. Rollback: `ROLLBACK_ARGUS_PUERTA_07JUN2026.py`. Argus ya NO puede tocar el CCR.

## 3. ✅ Erik Gonzalez (cta0169, SUB-0324) — falsa alarma
Reportado "pagado pero no navega". Diagnóstico: en Odoo activo/pagado; en router perfil activo, conectado, **tráfico vivo ~14-20 Mbps, 29 conexiones a Internet** → SÍ navegaba. Era caché/sesión del lado del cliente. Fix: reiniciar su CPE/dispositivo.

## 4. 🧰 Módulo FSM "Gestión de Servicios" (días previos de esta sesión, ya en producción)
Releases v18.0.1.4.0 → 1.5.1: tablero global (todos ven todas las órdenes), calendario por equipo, filtros + colores por estado, fix "Análisis de Desempeño", visibilidad técnico/patrullero (solo sus tareas), app del técnico (`/tech/dashboard`: botón Salir, botones Guardar/Finalizar claros, login con marca, técnicos confinados a su app, ícono PWA escudo+desarmador, guía PDF). Usuarios de prueba Juan/Jesus. Detalle en memoria `project_fsm_gestion_servicios.md`.

## 5. 💻 Traspaso a la laptop (para retomar en la madrugada)
Bundle en `C:\Users\dell\Downloads\sentinela_handoff\`: llaves SSH, memoria (54 archivos), transcript de esta conversación (`claude --resume`), scripts/rollbacks PCC, handoff, y **datos de la VPN** (L2TP/IPsec, user enrique_laptop, con nota de WSL modo espejo para que Claude tenga acceso). Script `pcc_madrugada/copy_to_usb.sh` lo regenera (incluye llaves+memoria+transcript+VPN). `setup_laptop.sh` se corre en la laptop. Pendiente: copiar la carpeta DellCli completa (2.7G, pero solo ~60MB es Sentinela; excluir `proyecto aleasystem` 1.5G, `proyecto golfbookvip` 772M, `claude-env` 109M) si se quiere todo en la laptop.

## 6. 🔎 Suscripciones — diagnóstico de navegación + candado anti-facturas-dobles
- **v18.0.1.3.81 — "Validar Navegación":** botón en pestaña Diagnóstico (`action_validar_navegacion`, campo `nav_status`). Resuelve que "Conectada" (sesión PPPoE) NO = navegando. Distingue de verdad leyendo: (1) sesión PPPoE → conectado/desconectado; (2) perfil del secret == `argusblack_servicio_suspendido` → 🔴 SUSPENDIDO walled-garden; (3) conntrack: conexiones del cliente a IPs públicas con datos de vuelta → 🟢 NAVEGANDO. Veredictos: 🟢/🔴/🟠 Sospechoso/🟡 Idle/⚫ Desconectado. Validado: Erik (navegando), cta0005 (suspendido), cta0011 (baja).
- **v18.0.1.3.82 — candado anti-duplicado:** `_billing_generate_invoice` omite subs cuyo periodo (next_billing_date) ya tiene factura no cancelada. Evita facturas dobles.

## 7. 🧾 Incidente facturas dobles (Laura Garza / Mayra) — RESUELTO
Laura (SUB-0338) y Mayra (SUB-0311) tuvieron 2 facturas del mismo periodo: una "Renovación" (cron Odoo, 1-jun) + una "Adeudo"/"Cargo mensual" (5-jun). **Forense:** las "Adeudo" las creó SentiBot (= OdooBot/__system__ id 1) en un solo lote (5-jun 15:14:37) → firma de un **script puntual de Claude en sesión previa** que se saltó el método oficial (NO un cron, NO el usuario). El cron normal ya se auto-protege (avanza next_billing_date). Las 3 (Laura, Mayra, Yolanda SUB-0348) quedaron OK (cada quien pagó una). **Regla guardada en memoria:** nunca crear account.move de sub con scripts ad-hoc; usar `_billing_generate_invoice` (con candado).

---

## Estado de la red al cerrar (7-jun noche)
| WAN | Estado | Tráfico |
|-----|--------|---------|
| ether1 (Telmex ISP1) | ON | clientes WISP (todo) |
| ether2 (TotalPlay) | **OFF** | — |
| ether3 (Telmex ISP3) | **ON** | idle (posible failover) |

`foIsps={{1;1}}` · Argus desconectado del CCR · clientes estables.

**Próxima sesión: madrugada — cerrar el balanceo (combo1) + probar failover.**
