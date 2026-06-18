# Resumen de sesión — 17 de junio de 2026

## Central de Monitoreo — Ventana de atención: panel multi-evento/historial EN VIVO
**Necesidad (Enrique):** mientras se atiende una alarma, las señales/eventos que **siguen llegando del mismo cliente** (misma cuenta, otra zona, fallas tipo AC) deben aparecer **solos** en "Eventos Múltiples" e "Historial del panel (24h)" sin recargar ni salir del evento.

### Evolución (sentinela_monitoring v15.6 → v16.1)
1. **v15.6** — botón "Refrescar" en ambas pestañas + pestaña "Eventos Múltiples" siempre visible (antes se ocultaba si al abrir había 0).
2. **v15.7** — auto-refresco cada 10 s vía widget OWL (`view_widgets`), respetando la bitácora.
3. **v15.8** — el botón "Refrescar" de servidor **cerraba la ventana** (un wizard que devuelve False cierra el diálogo) → se pasó a refresco **client-side** dentro del widget.
4. **v15.9** — quitado el botón manual (el auto cada 10 s lo hace innecesario).
5. **v16.0** — auto-refresco robusto: persiste la bitácora y refresca aunque el form esté "dirty" (antes el guard `isDirty` lo saltaba casi siempre); solo se detiene mientras se teclea.
6. **v16.1 (DEFINITIVO)** — **panel autónomo**: el widget OWL hace **polling propio al servidor** (`alarm.event.get_attention_companion_data`) cada 10 s y **pinta sus propias tablas** (eventos abiertos del cliente + historial 24h). **NO depende del registro transitorio del wizard ni de `record.load()`** → por eso ahora SÍ refleja lo que llega después. Las dos pestañas se unieron en **"🔁 Multi-evento e Historial (en vivo)"** + indicador "🔄 En vivo (cada 10 s) · última" + botón "Cerrar TODOS en bloque".

### Diagnóstico del "no llegan"
El backend SIEMPRE estuvo correcto (verificado en shell: la señal E301/fallo AC se recibió, creó evento, y `get_attention_companion_data` devolvía 25 señales incl. E301 + los eventos abiertos). El problema era **client-side**: el repintado del modal dependía de `record.load()`/estado dirty, poco confiable. La solución v16.1 (widget que lee y pinta solo) lo resuelve de raíz.

### Notas técnicas
- **`get_attention_companion_data()`** (alarm_event.py): devuelve `{sibling_count, siblings[], signal_count, signals[]}` con fechas formateadas en TZ del usuario (`format_datetime`). Eventos abiertos del mismo `partner_id` (no resueltos/cerrados) + señales del `device_id` en 24 h.
- **Trampa Odoo/OWL:** en un wizard (diálogo), un botón `type="object"` que retorna `False`/`None` **cierra el diálogo**. Para refrescar sin cerrar → hacerlo client-side (widget OWL), no con botón de servidor.
- **`action_refresh_related`** quedó en el wizard pero ya no se usa (el widget consulta directo el método del evento).

### Estado al cierre
- **sentinela_monitoring 18.0.1.16.1** en prod V18, 0 errores, HTTP 200, assets regenerados.

## Pendiente para la próxima sesión
1. **Probar el panel en vivo tras Ctrl+Shift+R** (cargó JS nuevo): abrir evento → pestaña "Multi-evento e Historial (en vivo)" → mandar señal con el emulador → debe aparecer sola en ~10 s sin salir del evento.
2. Sigue pendiente (de 16-jun): **validar el ciclo completo de patrullaje** end-to-end (despacho→push Manuel→app→cómo llegar→geocerca→dictamen→finalizar→reporte cliente) y **capturar coordenadas reales** en las suscripciones.

---

# Sesión 17-jun (parte 2) — Modelo Securithor + rediseño del dashboard (monitoring 18.0.1.16.1 → 18.0.1.29.1)

Maratón de tarde/noche sobre `sentinela_monitoring`. **23 releases.** Todo en prod (`Sentinela_V18`), commiteado, tageado y pusheado.

## A. Sirena por prioridad + esquema por TIPO (Securithor Opción A)
**Detonante:** la sirena ya funcionaba (servicio OWL `alarm_service.js` polla `get_audio_state` y reproduce `priority_sound` en loop), pero la prioridad crítica que usaban los 56 códigos `alarm` estaba **muda** (sin MP3).

- **v17.0** — Reordenó la semántica de prioridades: **`level` 1 = la MÁS importante** (antes crítico=100). `level` es único. Esquema base 3 niveles. Arregló cron offline (apunta `code='FALLA'`, no `level`), `create_fsm_order` (urgente por `sla<=5`), `alarm_service.js` (suena el menor level primero). Archivó 2 prioridades críticas duplicadas (campo `active` nuevo).
- **v18.0 (Fase 2)** — Una **prioridad-perfil por TIPO** con su sirena: `CRIT_FIRE` Incendio (11x) · `CRIT_INTRUSION` Intrusión (13x) · `CRIT_MEDICAL` Médica (100-102) · `CRIT_GEN` General (12x/14x/15x-16x/2xx) · `FALLA` (trouble+offline) · `RUTINA`. Los 56 códigos `alarm` reasignados por familia Contact-ID.
- **Audios cargados (UI/shell):** Enrique pasó Priority1–10.wav + Reminder.wav. Mapeo priorityN→levelN: Incendio=Priority1, Intrusión=Priority2, Médica=Priority3, General=Priority4, Falla=Priority5. Reminder.wav agregado al módulo (`static/src/sounds/reminder.wav`) para el modo tenue.

## B. Fases 1, 3, 4 del modelo Securithor
- **Fase 1 (v17.1)** — `process_signal_from_receptor` resuelve prioridad **por cuenta**: override `device.alarm.config` → código global → default id 35. Probado real (cuenta 0001, code 130 → level override).
- **Fase 3 (v19.0/.19.1)** — **Notificación instantánea al cliente** (`_dispatch_client_notification`, hook en ingesta). Flags efectivos por cuenta o globales (`notify_email/telegram/whatsapp` en `alarm.code`, `device.alarm.config`, `alarm.code.template.line`). Canales email/Telegram/WhatsApp, fail-safe por canal. Mensaje con tipo + zona + **domicilio + liga Google Maps**. Probado real (Telegram al cliente). **SMS a celular PENDIENTE: no hay gateway** (floLIVE solo a SIM IoT por ICCID).
- **Fase 4 (v20.0)** — Plantillas usables: botones `action_load_all_codes`/`action_load_attention_codes` pueblan desde el catálogo (idempotentes); líneas con código+descripción+categoría; `action_apply_template` pide confirmación; config por cuenta muestra descripción.

## C. Rediseño del dashboard del operador
- **v21.0/.21.1** — Tráfico "En vivo": **columna Prioridad con color** + **doble-clic abre el evento** (sin botón). Fix: `_prepare_signal_list` reventaba con señales de cuarentena (device_id False).
- **v22.0** — Wizard de atención: separadas otra vez **"Activas por procesar"** y **"Historial 24h"** (dos widgets OWL, antes unidas en v16.1).
- **v23.0** — **Tono tenue mientras se atiende**: si el operador tiene un evento tomado (`attending`), las DEMÁS alarmas suenan `reminder.wav` a volumen 0.35 cada 30s en vez de la sirena (para poder hablar por teléfono). Al cerrar/soltar, vuelve la sirena.
- **v24.0** — Tráfico **"Comentadas"** = eventos cerrados con `resolution_notes` (antes filtraba señales por `operator_notes`, vacío). Tabla propia con motivo + comentario.
- **v25.0/.26.0** — **Filtros por columna** (tipo Excel) combinables AND. v25 client-side; v26 **server-side** (busca en TODO el historial al filtrar, debounce 300ms, tope 300; sin filtro = 200 recientes). Mapeo columna→dominio.
- **v26.1** — **Fix zona horaria**: el dashboard mostraba horas en UTC; ahora `_fmt_local` (context_timestamp) → hora del operador (`America/Matamoros`). Aplica a receptor, fecha de señales, inicio y cierre.
- **v27.0/.29.0/.29.1** — **ALARMAS y PENDIENTES** unificadas a la tabla estándar (prioridad/color, filtros, doble-clic, sin botón Atender/Retomar). **Muestran EVENTOS** (no señales) vía `_prepare_events_as_signals` — 1 fila por evento, cuadra con el contador e incluye troubles offline sin señal.

## D. Cierre de evento (Opción C) — v28.0
"Resolver y cerrar" tronaba con "operación no válida" si faltaba el motivo. Ahora ese botón lleva a un **paso de cierre enfocado** (`state='close'`): muestra solo Motivo (obligatorio, resaltado) + Comentario, ocultando lo operativo. Tres botones: **← Regresar** (`action_back_from_close`), **🕓 Seguimiento (pausar)** (`action_pause_event`, cierre parcial para retomar, p.ej. hasta que llegue el patrullero), **✅ Cerrar evento** (`action_finalize`). Navegación con patrón `_reopen()` (no cae en la trampa del diálogo que se cierra al retornar False).

## E. Limpieza de datos de prueba
Borradas **5259 filas** de `device.alarm.config` en 263 dispositivos que apuntaban TODAS a la prioridad archivada id 39 con `notify_email`+`notify_telegram`=True (seed viejo de apply_template). Con Fase 3 viva habrían spameado a todos los clientes en cada señal. Enrique confirmó: módulo en desarrollo, no en uso → borrado seguro.

## Estado al cierre
- **sentinela_monitoring 18.0.1.29.1** en prod, 0 errores, HTTP 200.
- Cron de detección offline **reactivado** (se pausó durante las pruebas; reactivado al cierre).

## Pendientes para la próxima sesión
1. **Enrique (UI, sin deploy):** afinar audios por perfil si quiere; marcar qué códigos notifican al cliente y por qué canal; armar plantillas maestras (Residencial/Comercial) y aplicarlas a cuentas.
2. **SMS al celular del cliente:** elegir gateway (Twilio/Labsmobile/etc.) — floLIVE no sirve para teléfonos normales.
3. **Decisión:** ¿eliminar el sub-filtro "Activos" de Tráfico (redundante con ALARMAS)?
4. **Posible:** ¿sacar los troubles offline (Falla) de la pestaña ALARMAS para que solo muestre emergencias reales? (Enrique lo dejó así por ahora.)
5. Pendientes viejos: validar ciclo completo de patrullaje end-to-end; capturar coordenadas/`device.location` reales por cuenta.
