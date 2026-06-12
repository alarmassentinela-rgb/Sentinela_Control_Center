# Anexo — Retiro del switch Planet GSW-2401 (consolidar gestión en el CCRsentinela)

**Fecha:** 11-jun-2026 · **Anexo de:** `CUTOVER_CCR2004_11JUN2026.md` · **Topología:** [[reference-topologia-fisica-planta-wisp]]

> Intervención **independiente** del cutover del CCR2004. Se ejecuta en **su propia ventana** (no mezclar). Objetivo: eliminar el switch no administrado Planet GSW-2401 (punto único de falla sin valor) y dejar que el **CCRsentinela** haga de switch para la red de gestión `10.10.10.x`, con hardware offload.

---

## 1. Situación actual
- **Planet GSW-2401** (24p, **no administrado**, sin IP, invisible a la gestión). Nodo central del site.
- A él van **solo 4 cables**: CCRsentinela (`ether5 Lan1` = 10.10.10.254), EdgeSwitch `.59`, EdgeSwitch `.60`, y UISP Console `.11`.
- Toda la red de gestión+antenas `10.10.10.0/24` es **un L2 plano sin VLANs** (confirmado en los EdgeSwitch: solo VLAN1, untagged). También vive en ese segmento la red `192.168.33.0/24` ("puente temporal migración antena 33.200").

```
ANTES:
  CCRsentinela ether5 ── Planet GSW-2401 ─┬─ EdgeSwitch .59 ─ antenas/sectoriales
   (10.10.10.254 +                         ├─ EdgeSwitch .60 ─ antenas
    192.168.33.254)                        └─ UISP Console .11
```

## 2. Diseño objetivo
El CCRsentinela (CCR1016-12G, ROS 6.49.8) reemplaza al Planet con un **bridge por hardware**. Los 3 equipos se conectan a 3 puertos libres del router (hay 6 libres: `ether7–12`).

```
DESPUES:
  CCRsentinela  [ bridge-gestion ]  (RSTP, hardware offload)
       ether7 ── EdgeSwitch .59 ─ antenas/sectoriales
       ether8 ── EdgeSwitch .60 ─ antenas
       ether9 ── UISP Console .11
       (IPs 10.10.10.254/24 + 192.168.33.254/24 montadas en el bridge)
       (Planet GSW-2401 = ELIMINADO ; ether5 queda libre)
```

**Principios:**
1. **Un solo segmento plano** (sin VLANs), idéntico a hoy → la UISP sigue descubriendo y gestionando las antenas por L2.
2. **Hardware offload obligatorio**: el switch-chip del CCR1016 conmuta a wire-speed sin tocar CPU. Sin offload, el CPU del router se satura con el tráfico de las antenas.
3. **RSTP activo** en el bridge (igual que hoy en los EdgeSwitch) como colchón anti-loop durante el recableo.

---

## 3. ⚠️ Verificación previa OBLIGATORIA — switch-chip para el offload
El hardware offload solo funciona si **los puertos del bridge pertenecen al mismo switch-chip**. En la terminal del CCRsentinela:

```rsc
/interface ethernet switch print
/interface ethernet switch port print
```

- Elegir 3 puertos libres que estén en el **mismo `switch`** (ej. si `ether7/8/9` caen en el mismo chip, usarlos; si no, escoger el trío que sí comparta chip).
- Anotar el chip antes de seguir. Si ningún trío libre comparte chip, el offload quedará parcial → evaluar (aún funciona, pero parte del switching cae a CPU).

---

## 4. Script (aplicar en la ventana)
> Sustituir `ether7/8/9` por el trío validado en el paso 3.

```rsc
# 1) Bridge de gestión con RSTP
/interface bridge add name=bridge-gestion protocol-mode=rstp comment="Reemplaza Planet GSW-2401 (gestion 10.10.10.x)"

# 2) Agregar los 3 puertos con hardware offload (hw=yes)
/interface bridge port add bridge=bridge-gestion interface=ether7 hw=yes comment="EdgeSwitch .59"
/interface bridge port add bridge=bridge-gestion interface=ether8 hw=yes comment="EdgeSwitch .60"
/interface bridge port add bridge=bridge-gestion interface=ether9 hw=yes comment="UISP Console"

# 3) Mover las IPs de ether5 al bridge  (cortan la gestion un instante: hacerlo en ventana)
/ip address add address=10.10.10.254/24 interface=bridge-gestion comment="Gestion antenas (ex-ether5)"
/ip address add address=192.168.33.254/24 interface=bridge-gestion comment="Puente migracion antena 33.200 (ex-ether5)"
/ip address remove [find interface="ether5 Lan1" and address~"10.10.10.254"]
/ip address remove [find interface="ether5 Lan1" and address~"192.168.33.254"]
```

> Nota: si hay reglas (NAT/mangle/firewall/DHCP) que referencian `in/out-interface="ether5 Lan1"` para la red de gestión, repuntarlas a `bridge-gestion`. Revisar antes con:
> `/ip firewall nat print where in-interface="ether5 Lan1"` · `/ip firewall mangle print where ...` · `/ip dhcp-server print`.

---

## 5. Checklist de la ventana (orden)
**Preparación:**
- [ ] Backup del CCRsentinela: `/export file=ccr1016_pre_planet` + respaldo binario.
- [ ] Paso 3 hecho: trío de puertos del mismo switch-chip elegido.
- [ ] Revisar reglas que apunten a `ether5 Lan1` (NAT/mangle/DHCP/rutas) y tener listo el repunte a `bridge-gestion`.

**Ejecución:**
1. [ ] Crear `bridge-gestion` + agregar los 3 puertos con `hw=yes`.
2. [ ] **Recablear** (un equipo a la vez, verificando ping tras cada uno):
   - EdgeSwitch `.59` → `ether7`
   - EdgeSwitch `.60` → `ether8`
   - UISP `.11` → `ether9`
3. [ ] Mover las IPs `10.10.10.254/24` + `192.168.33.254/24` de `ether5` al `bridge-gestion`.
4. [ ] Retirar el Planet GSW-2401. `ether5 Lan1` queda libre (dejar disabled o re-rotular).
5. [ ] Repuntar cualquier regla que aún cite `ether5 Lan1`.

## 6. Verificación
- [ ] `/interface bridge port print` → los 3 puertos muestran la **H** de hardware offload activo.
- [ ] CPU del router estable (`/system resource print` → load bajo; si sube al mover tráfico = offload NO está activo → revisar chip).
- [ ] Ping a EdgeSwitch `.59`/`.60`, UISP `.11`, y a varias antenas `10.10.10.x`.
- [ ] **UISP ve las antenas** (estado online en la consola) y monitoreo OK.
- [ ] Clientes WISP sin afectación (PPPoE arriba, `/ppp active print`).
- [ ] Red `192.168.33.x` (puente antena 33.200) sigue alcanzable.

## 7. Rollback (rápido)
1. Reconectar los 4 cables al Planet GSW-2401 (CCRsentinela ether5 + 2 EdgeSwitch + UISP).
2. Volver las IPs `10.10.10.254/24` + `192.168.33.254/24` a `ether5 Lan1`.
3. `/interface bridge remove bridge-gestion` (y quitar sus puertos).
4. Repuntar reglas a `ether5 Lan1` si se cambiaron.
5. Verificar gestión de antenas y clientes.

---

## 8. Notas
- **Beneficio:** se elimina un SPOF no administrado; la gestión de toda la planta queda en un equipo administrable (visibilidad por puerto, RSTP, control).
- **Sin VLANs:** se mantiene el L2 plano actual; este anexo NO introduce segmentación (eso sería un proyecto aparte si algún día se quiere aislar gestión/antenas/cámaras).
- **Capacidad de puertos:** tras esto el CCRsentinela usa ether1(uplink), ether4(clientes), ether7/8/9(gestión); quedan ether5, ether6, ether10–12 libres.
- **Orden recomendado:** ejecutar DESPUÉS del cutover del CCR2004 (`CUTOVER_CCR2004_11JUN2026.md`), en ventana separada.
