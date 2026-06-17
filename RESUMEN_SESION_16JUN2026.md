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

---

# GPS / SentiCar — Integración con Suscripciones (sesión paralela)

Trabajo sobre `sentinela_subscriptions` (releases 18.0.1.3.91 → **18.0.1.3.99**) e infra de SentiCar/Traccar. Todo desplegado en STAGING + V18 y verificado. Detalle en memoria [[project-gps-subscriptions]] y [[reference-senticar-traccar]].

## Automatización de comandos SMS GPS (v.91 → v.93)
- **v.91** Catálogo `sentinela.gps.command.template` (plantillas por familia/acción con placeholders `{apn}{server}{port}{pwd}{imei}`); el operador elige y el comando se arma solo. Seed N01K/GT06 + Coban. Menú en Config + ACL + params.
- **v.92** `{server}` = **dominio** `gps.senticar.com` (no IP, resiliente a cambio de IP); GT06 corregido a modo 1 (`SERVER,1,...`). ⚠️ gotcha noupdate: el seed ya instalado se corrigió por SQL.
- **v.93** Botones GPS reubicados a su sección (Enviar SMS / Diagnóstico / link). ✅ **Probado real** en un N01K de la flota (sesión previa lo confirmó).

## Endurecimiento integración SentiCar (análisis P0/P1/P2)
- **P0 infra Traccar** (`/home/egarza/traccar/`): DB H2 + web migrados a **volúmenes** (`./data`/`./web`); **backup diario** 03:30 (rota 14d, `backup_traccar.sh`); pass admin id=1 rotada (`Lcs1992`→`i8dl1QirG0p8DI#6`); imagen **pineada** al digest de **6.14.4** (no `:latest`). Respaldo pre-migración + compose `.bak`. Verificado: 6 devices + 10 usuarios intactos.
- **P1 #6 reconciliación (v.94):** cron 6h `_cron_senticar_reconcile` + flag `senticar_state` por equipo + botón por sub. Detecta/auto-corrige desajustes del flag `disabled` (kill-switch param). Probado: 1 auto-corregido real.
- **P1 #5/#7/#8/#9/#10 (v.95):** IMEI único (constraint), rotar/revocar enlace portal, limpieza de share-links vencidos (cron+cap horas), sync email cliente→Traccar, params SentiCar en Ajustes.

## Grupos SentiCar (v.97 Fase 1 + v.99 Fase 2)
- **Fase 1 (v.97):** 1 grupo Traccar por cliente; los equipos heredan visibilidad (en vez de ligar equipo-por-equipo). Alta + reconciliación crean/asignan/comparten el grupo. Migrados los 6 equipos a 2 grupos.
- **Fase 2 (v.99):** jerarquía/reseller automática — campo `senticar_distributor_id` ("cuelga de") + grupo raíz paraguas. Anida el grupo del cliente bajo el del distribuidor y comparte hacia arriba. ✅ **Probado real**: DANIA bajo Sentinela → la flota vio en su sesión los 6 equipos (5 propios + el de DANIA); revertido.
- **🔑 Aprendizaje Traccar:** el query admin `?userId=X` muestra SOLO permisos directos (engaña); en la **sesión real del usuario** sí se ven los del grupo, **y la visibilidad se hereda hacia abajo** en el árbol. Verificar SIEMPRE logueando como el usuario.

## Manual de usuario
Generado **`Manual_Plataforma_SentiCar.pdf`** (13 pág, reportlab; fuente `gen_manual_senticar.py`) con secciones de integración, altas, diagnósticos, suspensiones y jerarquía, con ejemplos. **Enviado a Telegram** como "Plataforma SentiCar.pdf".

## Notas / incidencias GPS
- **Colisión de versiones con esta sesión paralela:** la de coordenadas tomó .94/.96/.98 → GPS quedó Fase1=.97, Fase2=.99 (commit `7ce2ab1`). Tags `.91`–`.99` pusheados.
- Conflicto de concurrencia (`SerializationFailure`) en el `-u` de V18 por las dos sesiones desplegando el mismo módulo a la vez → resuelto reintentando.

## Pendientes GPS/SentiCar
1. **Revocación automática de distribuidor:** hoy el share es aditivo; cambiar/quitar distribuidor no retira el acceso viejo (manual). Mejora futura.
2. **Capturar ICCID** en las subs GPS reales de clientes (para diagnóstico/SMS/registro por cliente).
3. **Limpiar cuentas demo** de la jerarquía SentiCar (Grupo SentiCar id7 / Distribuidor Demo id8 / Subcliente A id9 / B id10).
4. Rotar pass admin SentiCar id=5 (hijo). Reseller automatizado fino, Stripe live/SaaS, app iOS.

---

## Central de Monitoreo + FSM Patrullaje (continuación, noche 16-jun)

### Autorización de servicio (patrulla con cobro) — link Telegram
- **Bug "link no válido":** el token (`token_urlsafe`, con `_`/`-`) se enviaba **desnudo** en un mensaje Telegram con `parse_mode='Markdown'` → Telegram interpretaba los `_` como itálica y **rompía la URL**. FIX doble: `token_hex(20)` (solo 0-9a-f) + URL como enlace Markdown `[texto](url)`. (monitoring v14.15/.16) **Verificado real: el cliente autorizó.**
- **Claim al abrir wizard (v14.14):** re-toma el claim si el evento no está resuelto/cerrado (antes solo si `active`) → evita "Toma el evento antes de operarlo" al despachar un evento ya reconocido.

### Rastreo de patrulla en vivo (SentiCar) — `/SentiCar/rastreo/<token>`
- **Bug 404:** el controller `tracking_portal.py` **nunca se importaba** en `controllers/__init__.py` → la ruta no se registraba. FIX: agregado el import (fsm v7.2). El link al cliente abre.
- **Bug "isla nula" (pin en África):** Traccar devuelve **0,0** cuando el device no tiene fix GPS real (caso N01K heredado). FIX: `get_last_location_from_traccar` descarta 0,0 como "sin señal" + el mapa del cliente **no dibuja el pin** hasta tener posición válida (muestra "🛰️ Esperando señal GPS…"). (fsm v8.5)
- **Destino del mapa/"Cómo llegar"** apuntaban a `service_address` (vacío) → ahora usan **`install_lat/install_lon`** (coords de la alarma).

### Catálogo de Unidades de Patrulla (modelo nuevo `sentinela.patrol.unit`)
- **Concepto clave (2 cosas distintas):** la **UNIDAD** (celular compartido o vehículo, dispositivo SentiCar con `deviceId`) es lo que **se rastrea** por GPS; el **PATRULLERO** es un **usuario del sistema** marcado "Es Patrulla" que **trabaja la orden** en la app FSM (push, tareas, check-in, evidencias, cierre). Encajan: en el celular compartido, cada turno entra a Odoo con SU usuario; la app SentiCar reporta bajo el `deviceId` del celular.
- Modelo en `sentinela_fsm` (`is_patrol` vive en monitoring que está por encima → el filtro `is_patrol` va solo en el wizard, no en el campo del modelo fsm). Campos: tipo (celular/vehículo), `traccar_device_id`, placa, disponible, `is_default_dispatch` (solo una). Menú en Config de FSM y de Monitoreo.
- **Seed:** 🚓 Sentinela - March (deviceId 5) + 📱 Celular Patrullero 1 (deviceId 4, default despacho). Ambos reportando en SentiCar.
- **Wizard "Enviar Patrullero":** Unidad (obligatoria, default=celular compartido) + Patrullero (usuario `is_patrol`). Orden guarda `patrol_unit_id`; rastreo = unidad → fallback celular del patrullero.
- **Usuario creado: Manuel Sandoval** (`manuel.sandoval`/`Sentinela1`, interno + grupo FSM + is_patrol + unidad default March, reutilizando su contacto id 26095).

### Depuración del formulario de orden del patrullero (`tech_order_view`)
- **500 al abrir orden:** la plantilla usaba `subscription.keyword` (no existe) → cambiado a `security_code` (Clave de Seguridad de voz). (fsm v8.6)
- **"Cómo llegar"** ahora abre **navegación real** Google Maps + Waze (turn-by-turn) al domicilio. (SentiCar **solo rastrea, no navega**.)
- **Patrullaje depurado (v8.8):** oculta pestaña **Datos Técnicos** + tarjeta **Cita Programada**; **checklist propio** de patrullaje (solo 5 ítems: puertas/ventanas/perímetro/iluminación/sospechosos — `_populate_checklist` ya no mezcla las 'all' de instalación en patrol); **dictamen** (resultado+intrusión+policía) **movido DENTRO del form** (estaba fuera → no se guardaba).
- **Geocerca en "Llegada al sitio" (v8.9):** el handler `/arrival` valida la distancia GPS↔domicilio (Haversine); solo confirma (y notifica al cliente) si está dentro del radio. Param `sentinela_fsm.arrival_geofence_m` (default **150 m**, editable en Ajustes→Técnico→Parámetros). Si la cuenta no tiene coords, se omite la validación.

### Coordenadas (Categoría 1 = dirección instalación)
- Device hereda lat/lon de la suscripción (solo consulta); quitado el campo "Ubicación" del device. (monitoring v14.12/.13) — fuente única = suscripción (pestaña Instalación).

### Versiones al cierre
- **sentinela_fsm 18.0.1.8.9** · **sentinela_monitoring 18.0.1.15.5**. Todo en prod V18, 0 errores, HTTP 200.

### Pendientes patrullaje/monitoring
1. **Validar ciclo completo de patrullaje de punta a punta:** despacho → push a Manuel → app (orden limpia) → "Cómo llegar" → geocerca "Llegué" (probar lejos=rechaza / en sitio=confirma) → dictamen → finalizar → reporte al cliente. (Hoy se probó por partes.)
2. **Capturar coordenadas reales** en las suscripciones (sin coords la geocerca se omite).
3. Editar/ampliar el checklist de patrullaje si se requieren más ítems (plantillas tipo "Patrullaje").
4. Limpiar dispositivos de prueba SentiCar (N01K device 1 = 0,0; celular PAT-001 si aplica).

---

## Pendientes para la próxima sesión (WISP)
1. **Migración de los 3 enlaces** (Saucito, Rusias, Cd Industrial) de la oficina vieja a la nueva: los enlaces nuevos `.227` (Saucito) y `.251` (Rusias) ya están montados/inactivos esperando el cambio. Tras migrar, eliminar la dependencia del brinco provisional `.40/.41`.
2. **`.64` Saucito EdgePoE 8xp dañado** — reemplazo pendiente.
3. **Seguridad del inventario**: cifrar el Excel y plan de rotación de passwords de gestión por sitio.
4. Limpieza UISP (de sesiones previas, sigue pendiente): inyectar key a ciegas, archivar muertas, renombrar sitio "Caballero Hilario, MIguel Angel" → Brisas/Quinta Real.
