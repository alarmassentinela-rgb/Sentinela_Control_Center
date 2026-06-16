# Resumen de Sesión — 16 de junio de 2026

Sesión enfocada en **infraestructura de red WISP / netwatch**. Sin cambios de módulos Odoo.

## Red WISP — Reconciliación inventario netwatch vs "Relacion ip antenas.xlsx"

### Punto de partida
Enrique pidió analizar `~/Downloads/Relacion ip antenas.xlsx` (inventario completo de equipos de la red WISP: 57 IPs con SSID, claves WPA2, usuarios, canal y frecuencia) y cruzarlo contra el inventario de `sentinela_netwatch` (`inventory.json`, 53 dispositivos).

### Hallazgo grande: punto ciego de alertas
- **`.40` / `.41` = enlace PROVISIONAL 6 GHz entre oficina vieja ↔ oficina nueva**, estaban como `tipo=desconocido` → **NO alertaban a Telegram**.
- Es el eslabón que hoy lleva a la oficina nueva los **3 enlaces SIN migrar** (Saucito, Rusias, Cd Industrial). Si se cae, esas 3 radio bases quedan aisladas y netwatch se quedaba callado.

### Topología real de Saucito (aclarada por Enrique)
```
Saucito (.252, lado Saucito) ↔ .228 (lado of.vieja) → brinco provisional .41(of.vieja)↔.40(of.nueva) → oficina nueva
```
- Enlaces NUEVOS montados esperando migración: **`.227`** (Saucito) y **`.251`** (Rusias, montado en of. nueva).
- El `inventory.json` los tenía mal rotulados: `.251`="Base-PK" (¡Parker!), `.227`/`.252` duplicados "BaseSaucitoR5ac", `.228` como `estacion` (no alertaba).

### Fixes aplicados a `inventory.json` + desplegados
Deploy = rsync a `egarza@192.168.3.2:~/sentinela_netwatch/inventory.json` + `docker compose restart netwatch`.

| IP | Antes | Ahora |
|---|---|---|
| `.40` `.41` | `desconocido` (no alertaba) | `enlace` "Provisional Of.Nueva/Vieja" → **alerta ON** |
| `.228` | `estacion` (no alertaba) | `enlace` "Saucito lado Of.Vieja (activo)" |
| `.252` | `sectorial` mal rotulado | `enlace` "Saucito lado Saucito (activo)" |
| `.227` | duplicado "BaseSaucitoR5ac" | `enlace` "Saucito – enlace NUEVO (por migrar)" |
| `.251` | `Base-PK` (Parker) | `enlace` "Rusias – enlace NUEVO (por migrar)" |

**Verificado vivo** (`/api/status`): `.40/.41/.228/.252/.251` = up; `.227` = inactivo (correcto, desconectado). 0 down.

## Enlace de casa de Egarza (`.200/.201`) — segmento correcto

### Análisis
- Es un enlace **privado** de Enrique (su casa), NO infra WISP. Vive en el **switch de oficina** (segmento `192.168.3.x`).
- En modo **bridge**, la casa ve la LAN del switch donde está enchufado el radio base. Office switch → ve LAN oficina (lo que Enrique quiere). Si se moviera al switch WISP → vería `10.10.10.x` y PERDERÍA la oficina.
- **Regla clave**: la IP de gestión del radio debe coincidir con el segmento donde está enchufado. Mezclar (radio en switch oficina con IP `10.10.10.x`) lo deja huérfano e inalcanzable — fue justo lo que pasó cuando Enrique la cambió a `10.10.10.200`.

### Corrección (rectifiqué mi recomendación previa)
Inicialmente recomendé mover la gestión a `10.10.10.x` (Opción A); era incorrecto para este enlace porque vive en el segmento de oficina. Decisión final:
- **Monitorear en netwatch como `192.168.3.200/.201`** (netwatch corre en el server, misma LAN, los pinguea directo). Eliminadas las entradas `10.10.10.200/.201`.
- Enrique **regresó la IP de gestión** de los 2 radios a `192.168.3.200/.201`.

**Verificado vivo**: `192.168.3.200` y `.201` = 🟢 **up**. Resumen final: **48 up / 0 down / 6 inactivos**.

## Notas de seguridad (mencionadas, no accionadas)
- El Excel contiene TODAS las claves WPA2 y passwords de gestión en texto plano, en `Downloads`. Casi todos los equipos comparten `SentinelaW1sp` de gestión → si una antena se compromete, cae todo. Recomendado: guardarlo cifrado y a futuro rotar a passwords por sitio.
- El bridge del enlace de casa extiende el dominio L2 de la LAN del servidor de producción hasta la casa de Enrique (consideración de seguridad aceptada por conveniencia).

## Inconsistencias detectadas en el Excel (informativas, no corregidas)
- `SentinelaW1sp` vs `SentinelaWisp` (QR `.65` y UISP usan variante con "i").
- Equipos sin credenciales capturadas: `.210`, `.228`.
- Typo de canal "40hmz" en `.217/.233/.8`.
- `.64` Saucito 8xp marcado "Dañado".
- Switch `.65` Quinta Real usa `SentinelaWisp.` (no `SentinelaW1sp.`).

## Pendientes para la próxima sesión
1. **Migración de los 3 enlaces** (Saucito, Rusias, Cd Industrial) de la oficina vieja a la nueva: los enlaces nuevos `.227` (Saucito) y `.251` (Rusias) ya están montados/inactivos esperando el cambio. Tras migrar, eliminar la dependencia del brinco provisional `.40/.41`.
2. **`.64` Saucito EdgePoE 8xp dañado** — reemplazo pendiente.
3. **Seguridad del inventario**: cifrar el Excel y plan de rotación de passwords de gestión por sitio.
4. Limpieza UISP (de sesiones previas, sigue pendiente): inyectar key a ciegas, archivar muertas, renombrar sitio "Caballero Hilario, MIguel Angel" → Brisas/Quinta Real.
