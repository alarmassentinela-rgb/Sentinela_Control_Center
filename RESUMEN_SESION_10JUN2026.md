# Resumen de sesión — 10 de junio de 2026

Dos grandes bloques: **(A)** pruebas + fixes del módulo FSM (Gestión de Servicios), y **(B)** diseño y montaje del piloto de **atención por WhatsApp con Chatwoot**.

---

## A. Módulo `sentinela_fsm` — pruebas en STAGING + 2 bugs + 1 feature

Antes de probar se verificó que **prod (Sentinela_V18) y lab (Sentinela_STAGING) tenían la MISMA versión y código idéntico** (hash byte a byte de los 54 archivos .py/.xml, normalizando CRLF). Las pruebas se corrieron en STAGING vía `odoo shell` con rollback (sin ensuciar la DB).

### Escenarios probados (63 checks, todos PASS)
1. **Venta → orden automática** (15) — traslado, reactivación, suscripción nueva, producto opt-in `generates_fsm_order`.
2. **Ciclo de orden + sync al contrato** (18) — validaciones assign/finish, firma obligatoria, sync de datos técnicos, cierre por retiro, reprogramación de mantenimiento.
3. **Patrullaje + ETA** (14) — Haversine, anti-spam, cron de ETA, fallback Traccar→last_gps, arribo.
4. **Mantenimiento preventivo (cron) + inventario** (16) — cron crea/no duplica/avanza fecha; `_create_stock_moves` descuenta stock y sync de número de serie.

### Bugs corregidos y DESPLEGADOS a producción
- **v18.0.1.5.2** (commit `617f8de`, tag `v18.0.1.5.2-sentinela_fsm`):
  1. `sale_order.py:67` — detección de renovación usaba estado `'suspended'` (inexistente); el real es `'suspension'`. A un cliente suspendido que recompraba se le generaba orden de instalación indebida. **Fix:** `'suspended'`→`'suspension'`.
  2. `fsm_order.py` `action_finish` — escribía el campo inexistente `vehicle_brand_model` en `sentinela.subscription` → `ValueError` al cerrar órdenes GPS con marca/modelo de vehículo. **Fix:** mapear a `vehicle_brand` / `vehicle_model` (campos reales separados).

### Feature + bug de vista, DESPLEGADO a producción
- **v18.0.1.6.1** (commit `543a002`, tag `v18.0.1.6.1-sentinela_fsm`):
  - **Botón "Reconectar + Visita Técnica"** en la suscripción (estado `suspension`): reconecta el servicio (remoto) Y crea una orden `repair` urgente para verificar el CPE en sitio. **NO** automático en `action_reactivate` (eso generaría órdenes basura por cada pago). Reemplaza la rama huérfana de `sale_order.py` (`origin="Reactivación"`) que ningún flujo disparaba.
  - **Bug de vista preexistente destapado:** la vista FSM de la suscripción heredaba de `view_sentinela_subscription_form` (base, priority 1), pero la primaria es `view_sentinela_subscription_form_pro` (priority 0). Resultado: la pestaña "Historial Técnico (FSM)", el botón "Tickets" y los campos de mantenimiento estaban **invisibles** para el usuario. **Fix:** heredar de la vista PRO. (v18.0.1.6.0 quedó con xpath roto/ParseError; corregido en 1.6.1.)
  - **Pendiente anotado:** la vista de `sentinela_monitoring` también hereda de la base eclipsada → revisar si sus campos están igualmente ocultos.

Deploy con rsync → `-u` STAGING → `-u` V18 → restart web. Versión final en prod: **18.0.1.6.1**, HTTP 200, sin errores. Verificado que la vista primaria ya muestra las 4 features FSM.

---

## B. Atención por WhatsApp con Chatwoot — piloto montado y validado

Diseño cerrado con Enrique (ver memoria `project_reportes_whatsapp_chatwoot.md`, muy detallada). Decisiones: clientes con credenciales → portal `/my/services/new` (ya existe); sin credenciales → botón "Reportar por WhatsApp" (el cliente inicia → riesgo de baneo casi nulo); identificación por teléfono, sin match → orden "POR CONCILIAR"; atención humana centralizada en **Chatwoot** con handoff bot→recepción. Dos números reales (8688225875 reportes, 8681254500 cobranza), ambos hoy atendidos a mano desde celular, multi-tema.

### Montado (servidor 192.168.3.2)
- **Chatwoot** en `/opt/chatwoot` (docker compose: rails+sidekiq+postgres pgvector+redis, aislado). Web **https://chat.sentinela.mx** vía el **Cloudflare Tunnel existente** de senticar (se añadió ingress chat→localhost:3001 + CNAME proxied; radar intacto). v4.1.0, locale es.
- **EvoApi**: activado `CHATWOOT_ENABLED=true` + recreado servicio `evolution-api`. Instancia nueva **`SentinelaReportes`** vinculada al **8688225875** (por **pairing code**, no QR — el QR daba "intenta más tarde" por cooldown tras 5 intentos). Integración Chatwoot activa → inbox "Reportes Sentinela".
- **SMTP**: configurado con `mail.sentinela.com.mx:465 SSL` (mismo de Odoo). Envío de prueba OK → invitaciones de agentes por correo funcionan.
- **Cuenta admin**: `egarza@sentinela.com.mx` (contraseña temporal entregada en chat).

### Fixes / trampas resueltas (documentadas en memoria)
- **Onboarding loop:** crear el usuario por consola no limpia la clave Redis `CHATWOOT_INSTALLATION_ONBOARDING` → Chatwoot pedía "registrarse". Fix: borrar esa clave Redis.
- **Saliente roto:** el inbox quedó con `webhook_url=http://localhost:8080/...`; desde el contenedor de Chatwoot localhost≠EvoApi → ECONNREFUSED, las respuestas no salían. Fix: webhook_url → `http://192.168.3.2:8080/...` (verificado 200).

### Validado
**Flujo bidireccional probado:** mensaje entrante (WhatsApp→Chatwoot) y respuesta saliente (Chatwoot→WhatsApp) funcionando. El piloto está vivo.

### Entregable
PDF de documentación ("Sentinela — WhatsApp + Chatwoot + IA/Odoo", lenguaje claro, sin contraseñas) generado con reportlab y **enviado al Telegram de Enrique** (chat 7965190381).

---

## Pendientes para la próxima sesión
1. **Chatwoot — app móvil:** reinstalar en el celular para limpiar el caché del onboarding viejo (el servidor ya está validado por web).
2. **EvoApi — fix duradero del saliente:** cambiar `SERVER_URL` a `192.168.3.2:8080` (requiere reiniciar EvoApi en ventana tranquila) para que el webhook no vuelva a quedar en localhost si se reconfigura la integración.
3. **Fase IA + Odoo (Fase C):** bot de primera línea (menú reporte/pago/cotización/asesor) + integración Odoo XML-RPC (identificar cliente por teléfono, crear orden FSM con folio, handoff a recepción) + panel con ficha del cliente en Chatwoot.
4. **Dar de alta el equipo en Chatwoot** (recepción/ventas/cobranza) + crear equipos (Teams) y migrar la atención del celular a Chatwoot.
5. **Conectar el 8681254500** (cobranza) igual que el de reportes.
6. **Watchdog de cloudflared** ⚠️ — `chat` y `radar` dependen del mismo túnel; sigue sin watchdog (solo @reboot). Si crashea, caen ambos.
7. **FSM — revisar vista de monitoring** (`view_subscription_form_monitoring_inherit_v4`): hereda de la base eclipsada, sus campos podrían estar ocultos en la ficha de suscripción.

## Notas de infra tocada (rollback)
- Chatwoot es contenedores nuevos aislados; `docker compose down` en `/opt/chatwoot` lo retira sin afectar lo demás.
- EvoApi: backup del `.env` en `/home/egarza/evoapi/.env.bak_chatwoot_*` antes de habilitar Chatwoot.
- Túnel Cloudflare: se añadió ingress + DNS; quitar el ingress de `chat` y el CNAME revierte sin tocar radar.
