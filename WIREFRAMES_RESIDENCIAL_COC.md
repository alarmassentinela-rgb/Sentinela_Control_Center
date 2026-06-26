# Wireframes — Flujo Residencial · COC Sentinela

> Formato: Markdown/ASCII, versionable. Base para diseño visual (Figma) tras aprobación.
> Alcance: **cliente residencial** (alarma ± internet). Mobile-first.
> Cada pantalla indica su **Fase** del roadmap (PRD §10). Estado: borrador para revisión.
> Orden: Onboarding → Login → Dashboard → Seguridad → Facturación → Soporte → Mi Cuenta.

## Convenciones

- Ancho de mockup ≈ pantalla de celular. `●` verde/ok · `⚠` ámbar · `🔴` rojo · `▾` selector · `[ ]` botón · `(…)` campo.
- **Cabecera global:** saludo + (selector de domicilio si aplica) + 🔔 notificaciones + 💬 asistente (→WhatsApp en v1) + 👤.
- **Barra inferior (residencial, 5):** 🏠 Inicio · 🛡️ Seguridad · 🧾 Facturas · 🛠️ Soporte · 👤 Cuenta.
- **📞 Emergencia (persistente):** acceso "Llamar a Sentinela" siempre a ≤1 tap — botón flotante discreto en cabecera y acción central en *modo simple*. Función crítica en un producto de seguridad.
- **🏠 Selector de domicilio:** si el cliente tiene >1 dirección de servicio, aparece un selector en la cabecera; todo el contenido (estado, eventos, facturas) se filtra por el domicilio elegido. Con 1 solo domicilio, no se muestra.
- **Estados universales por pantalla:** Cargando (skeleton, no spinner) · Vacío (con propósito) · Error (reintentar) · Sin conexión (PWA, última info conocida).
- **Modo simple** (adulto mayor): tipografía +, botones grandes, acción única "Llamar a Sentinela".

---

# 1. Onboarding  [Fase 0]

### O-1 · Bienvenida
```
┌─────────────────────────────┐
│                             │
│         [ Logo ]            │
│        Sentinela            │
│                             │
│   Tu seguridad, en una      │
│   sola app.                 │
│                             │
│   ● Alarma · Internet · GPS │
│   ● Facturas y CFDI         │
│   ● Soporte en vivo         │
│                             │
│   [  Entrar  ]              │
│   ¿Primera vez? Es el mismo │
│   botón: usa tu WhatsApp.   │
└─────────────────────────────┘
```
- **Muestra:** marca (vía theme endpoint — costura branding), propuesta de valor en 3 puntos.
- **Acciones:** `Entrar` → Login. (No hay "registro" separado: el alta la hace Sentinela en Odoo; el cliente solo verifica su teléfono.)
- **Notas UX:** sin formularios largos; un solo botón. Tour (O-2) se muestra tras el primer login exitoso, no antes.

### O-2 · Tour rápido (3 tarjetas, tras primer login)
```
┌─────────────────────────────┐
│  ● ○ ○            Saltar     │
│                             │
│      [ ilustración ]        │
│                             │
│  Mira el estado de tu       │
│  hogar de un vistazo.       │
│                             │
│  [ Siguiente ]              │
└─────────────────────────────┘
```
- **3 pasos:** (1) Estado de tranquilidad, (2) Reportar y seguir al técnico, (3) Tus facturas y CFDI a un tap.
- **Acciones:** Siguiente / Saltar → O-3.

### O-3 · Checklist de configuración (mejora la calidad del servicio)
```
┌─────────────────────────────┐
│  Configura tu seguridad     │
│  Completa para protegerte    │
│  mejor:                      │
│  ☑ Verifica tu teléfono      │
│  ☐ Agrega contactos de       │
│     emergencia        [Hacer]│
│  ☐ Revisa tus zonas   [Hacer]│
│  ☐ Activa notificaciones[Hacer]│
│  ▓▓▓▓░░░  1/4 (25%)          │
│  [ Ir al inicio ]            │
└─────────────────────────────┘
```
- **Muestra:** checklist gamificado con barra de progreso; cada ítem lleva a la pantalla que lo resuelve (contactos S-5, zonas, notificaciones MC-4).
- **Por qué:** más contactos/zonas verificadas = mejor respuesta real del monitoreo. Reaparece como tarjeta en el Dashboard hasta completarse; se puede saltar.
- **Acciones:** `Hacer` (deep-link) · `Ir al inicio` → Dashboard.

---

# 2. Inicio de sesión  [Fase 0]

### L-1 · Ingresar teléfono (WhatsApp)
```
┌─────────────────────────────┐
│  ←                          │
│  Entra con tu WhatsApp      │
│                             │
│  Te enviaremos un código    │
│  por WhatsApp.              │
│                             │
│  País ▾ +52                 │
│  ( 868 123 4567        )    │
│                             │
│  [  Enviar código  ]        │
│                             │
│  ¿Prefieres contraseña?     │
└─────────────────────────────┘
```
- **Acciones:** `Enviar código` → L-2. Link "contraseña" → L-4 (para quien ya la creó).
- **Estados:** teléfono inválido (validación en vivo); rate-limit ("espera 30 s").
- **Edge — teléfono no encontrado (L-1b):** "No encontramos ese número. ¿Hablamos por WhatsApp para ayudarte?" `[Contactar a Sentinela]`. (No revelar si existe o no por seguridad: mensaje neutро + canal de ayuda.)
- **Origen:** gateway `find_partner_by_phone`; OTP por canal WhatsApp transaccional.

### L-2 · Código OTP
```
┌─────────────────────────────┐
│  ←                          │
│  Ingresa tu código          │
│  Enviado a +52 868 ••• 4567 │
│                             │
│   [ _ ][ _ ][ _ ][ _ ][_][_]│
│                             │
│  Reenviar en 0:42           │
│                             │
│  [  Verificar  ]            │
└─────────────────────────────┘
```
- **Acciones:** auto-avanza al 6º dígito; `Verificar`. Reenviar tras contador.
- **Estados:** código incorrecto (intentos restantes); expirado; bloqueo tras N intentos.
- **Origen:** gateway valida OTP → emite JWT (partner_id).

### L-3 · Asegura tu cuenta (solo primera vez, opcional)
```
┌─────────────────────────────┐
│  ¡Listo, Carmen! ✅          │
│  Asegura tu acceso (opcional)│
│                             │
│  [ Activar Face ID / huella ]│
│                             │
│  o crea una contraseña:     │
│  ( ••••••••           )     │
│                             │
│  [ Guardar ]   [ Ahora no ] │
└─────────────────────────────┘
```
- **Acciones:** activar biométrico; o crear contraseña; o "Ahora no" → Dashboard.
- **Notas:** biométrico se guarda en el dispositivo; acelera futuros ingresos (L-4).

### L-4 · Ingreso recurrente (rápido)
```
┌─────────────────────────────┐
│        [ Logo ]             │
│  Hola de nuevo, Carmen      │
│                             │
│      [ 👆 Face ID ]         │
│                             │
│  o  ( contraseña      )     │
│     [ Entrar ]              │
│                             │
│  Usar código por WhatsApp   │
│  ¿Olvidaste tu contraseña?  │
└─────────────────────────────┘
```
- **Acciones:** biométrico (1 tap) · contraseña · fallback OTP · recuperación (L-5).

### L-5 · Recuperación
```
┌─────────────────────────────┐
│  ←  Recuperar acceso        │
│  Te ayudamos por:           │
│  ( ) WhatsApp  ( ) Correo   │
│  [ Enviar código ]          │
└─────────────────────────────┘
```
- **Acciones:** elige canal → flujo OTP → permite nueva contraseña.

---

# 3. Dashboard / Inicio  [Fase 1]

### D-1 · Dashboard residencial — estado VERDE (95% del tiempo)
```
┌─────────────────────────────┐
│ Hola, Carmen 👋  📞 🔔 💬 👤 │
│ 🏠 Casa ▾  (si >1 domicilio) │
│ ╭─────────────────────────╮ │
│ │ ✅ Tu hogar está         │ │
│ │    protegido             │ │
│ │ ▁▂▃▅▃▂▁▂▃▅▃▂▁  (latido)  │ │
│ │ Última señal: hace 4 min │ │
│ │ 30 días sin incidentes   │ │
│ ╰─────────────────────────╯ │
│ ⚙️ Configura tu seguridad 3/4│  ← tarjeta onboarding (hasta completar)
│                             │
│ 🛡️ Alarma     🌐 Internet   │
│ ╭─────────╮   ╭─────────╮   │
│ │● En línea│   │● Conectado│  │
│ │Sin       │   │Señal buena│  │
│ │eventos hoy│  │45 Mbps    │  │
│ ╰─────────╯   ╰─────────╯   │
│                             │
│ 💡 Sin pendientes 🎉        │
│                             │
│ [ Reportar un problema ]    │
├─────────────────────────────┤
│ 🏠   🛡️   🧾   🛠️   👤      │
└─────────────────────────────┘
```
- **Muestra:** Estado de Tranquilidad (agregado), latido del panel, tarjetas por servicio activo, pendientes; **📞 emergencia** y **selector de domicilio** (si aplica) en cabecera; tarjeta de **checklist de onboarding** hasta completarse.
- **Acciones:** tap tarjeta → módulo; `Reportar` → SP-2; 📞 emergencia (1 tap); 🔔→N-1; 💬→WhatsApp; ⚙️ checklist → O-3.
- **Origen:** agregación en gateway (estado subs + last_communication + eventos + facturas).

### D-2 · Dashboard — estado ÁMBAR (pendiente)
```
│ ╭─────────────────────────╮ │
│ │ ✅ Tu hogar está         │ │
│ │    protegido             │ │
│ ╰─────────────────────────╯ │
│ ⚠ Pendiente                 │
│ ╭─────────────────────────╮ │
│ │ Tu factura de junio vence│ │
│ │ en 3 días                │ │
│ │ $450.00     [Ver/Pagar*] │ │  *Pagar = Fase 2; v1 = "Ver"
│ ╰─────────────────────────╯ │
```
- **Variantes de pendiente:** factura por vencer/vencida · contrato por firmar · autorización de patrulla pendiente · ticket con novedad.

### D-3 · Dashboard — estado ROJO (evento activo)
```
│ ╭─────────────────────────╮ │
│ │ 🔴 Evento en tu domicilio│ │
│ │ Alarma de intrusión      │ │
│ │ 14:32 · Zona: Cocina     │ │
│ │ Monitoreo atendiendo…    │ │
│ │ [ Ver detalle ]          │ │
│ ╰─────────────────────────╯ │
```
- **Acciones:** `Ver detalle` → S-3. Si hay patrulla, muestra "patrullero en camino".
- **Notas UX:** el rojo domina la pantalla; todo lo demás se atenúa.

---

# 4. Seguridad / Alarmas  [eventos Fase 1–2 · núcleo Fase 2]

### S-1 · Inicio de Seguridad
```
┌─────────────────────────────┐
│ ←  Seguridad                │
│ ╭─────────────────────────╮ │
│ │ ● Panel en línea         │ │
│ │ ▁▂▃▅▃▂▁ (latido)         │ │
│ │ Última señal: hace 4 min │ │
│ │ Energía: ⚡ CA presente   │ │
│ │ Batería: 87% (respaldo OK)│ │
│ │ Comunicación: ● IP + GPRS │ │
│ │ Señal: buena (-72 dBm)    │ │
│ ╰─────────────────────────╯ │
│                             │
│ Acciones                    │
│ [ Contactos de emergencia ] │
│ [ Equipos y mantenimiento ] │
│ [ Llamar a monitoreo ]      │
│ [ Modo Vacaciones* ]        │  *Fase 2
│                             │
│ Eventos recientes      Ver→ │
│ • 12-jun Apertura · Normal  │
│ • 03-jun Prueba · Normal    │
└─────────────────────────────┘
```
- **Muestra:** salud del panel — comunicación, última señal, **alimentación eléctrica (CA/respaldo)**, **nivel de batería**, **medio de comunicación (IP/GPRS/LTE/radio) + señal**, accesos rápidos, últimos eventos.
- **Acciones:** contactos (S-5) · equipos y mantenimiento (S-7) · click-to-call monitoreo · ver eventos (S-2).
- **Origen:** ♻️ `monitoring.device` (battery_level, signal_strength, last_communication, connection_mode) · 🔧 estado de CA derivado de eventos Contact-ID (E301/R301 pérdida/restablecimiento de energía) · 🆕 `get_health_status` + posible campo "medio de comunicación" si no existe hoy.
- **Estados:** sin CA → "🔋 En respaldo (batería)" ámbar; batería baja → rojo; panel sin comunicar > umbral → "🔴 Sin comunicación hace X".

### S-2 · Historial de eventos
```
┌─────────────────────────────┐
│ ←  Eventos        Filtrar ▾ │
│  Hoy                        │
│  🔴 14:32 Intrusión · Cocina│
│       Atendido · falsa alarma│
│  Esta semana                │
│  ● 12-jun Apertura · Puerta │
│       Normal                │
│  ● 03-jun Prueba de panel   │
│       Normal                │
│                             │
│  [ Cargar más ]             │
└─────────────────────────────┘
```
- **Muestra:** timeline (tipo, hora, zona, resolución/close_reason).
- **Acciones:** filtrar (activos/resueltos, tipo); tap → S-3.
- **Vacío:** "Sin eventos — eso es buena señal 👍".
- **Origen:** ♻️ `alarm.event` (scoped por record rule).

### S-3 · Detalle de evento (con patrulla)
```
┌─────────────────────────────┐
│ ←  Evento · Intrusión       │
│ 🔴 12-jun-2026 14:32        │
│ Zona: Cocina (Z3)           │
│ Estado: Resuelto            │
│ Resolución: Falsa alarma    │
│ Atendió: Op. Juan P. · 38 s │
│                             │
│ Patrulla despachada         │
│ ╭─────────────────────────╮ │
│ │ [ mapa patrullero ]      │ │
│ │ En sitio 14:51           │ │
│ ╰─────────────────────────╯ │
│                             │
│ [ Descargar reporte (PDF) ] │
│ [ Marcar como falsa alarma ]│
└─────────────────────────────┘
```
- **Muestra:** detalle completo + operador que atendió (señal de confianza) + patrulla (mapa/estado) si la hubo.
- **Acciones:** descargar reporte PDF (S-4) · marcar falsa alarma.
- **Origen:** ♻️ `alarm.event`, `_render_master_report_pdf`, `fsm_order` patrulla.

### S-4 · Reporte PDF (visor/descarga)
```
┌─────────────────────────────┐
│ ←  Reporte de incidente     │
│ [ vista previa PDF ]        │
│ [ Descargar ]  [ Compartir ]│
└─────────────────────────────┘
```
- **Acciones:** descargar / compartir (WhatsApp/correo).

### S-5 · Contactos de emergencia
```
┌─────────────────────────────┐
│ ←  Contactos de emergencia  │
│ 1. Carmen (titular) 868•••  │
│ 2. José (esposo)    868•••  │
│ 3. + Agregar contacto       │
│                             │
│ [ Guardar ]                 │
└─────────────────────────────┘
```
- **Muestra/Acciones:** ver/editar/ordenar contactos (orden = prioridad de llamado).
- **Nota:** parte del checklist de onboarding ("mejora tu servicio").

### S-6 · Autorizar patrulla (magic link, fuera de sesión)
```
┌─────────────────────────────┐
│  Sentinela                  │
│  ¿Autorizas el envío de una │
│  patrulla a tu domicilio?   │
│  Costo: $350.00             │
│  Evento: Intrusión 14:32    │
│  [ Autorizar ]  [ Rechazar ]│
│  Expira en 47:50            │
└─────────────────────────────┘
```
- **Acceso:** magic link por WhatsApp (sin login). ♻️ `service.authorization.token` (TTL + auditoría).

### S-7 · Equipos, mantenimiento y garantías  [Fase 2–3]
```
┌─────────────────────────────┐
│ ←  Equipos y mantenimiento  │
│ Mis equipos                 │
│ • Panel DSC PowerSeries     │
│    Propio · Inst. 2024      │
│    Garantía: vigente→mar-27 │
│    Vida útil: 78% restante  │
│ • Sensor PIR Cocina         │
│    Propio · Garantía vencida│
│                             │
│ Mantenimiento               │
│ Último: 12-mar-2026 ✅       │
│ Próximo recomendado:        │
│ 12-sep-2026  [ Agendar ]    │
│ Historial:                  │
│ • 12-mar Preventivo · OK    │
│ • 04-oct Correctivo · OK    │
└─────────────────────────────┘
```
- **Muestra:** equipos instalados (propiedad propio/leasing/comodato, fecha de instalación, **garantía**, **vida útil**), último mantenimiento, **próximo recomendado**, historial de mantenimientos.
- **Acciones:** `Agendar` mantenimiento (→ crea ticket tipo mantenimiento, SP-2/SP-3) · tap equipo → ficha.
- **Origen:** ♻️ mantenimientos = `fsm.order` (service_type=maintenance) · ♻️ próximo mantenimiento = `subscription` (cron preventivo / next_maintenance_date) · ♻️ propiedad/leasing = `subscription.equipment_ownership` + fin de leasing · **🆕 garantía + vida útil: requieren un registro de equipos con fechas de garantía/vida útil que hoy NO existe limpio (ver Decisión §pendientes).**
- **Estados:** garantía vigente (verde) / por vencer (ámbar) / vencida (gris); sin equipos registrados → "Aún no hemos registrado tus equipos".

---

# 5. Facturación  [Fase 1 · solo consulta]

### F-1 · Estado de cuenta
```
┌─────────────────────────────┐
│ ←  Facturación              │
│ ╭─────────────────────────╮ │
│ │ Adeudo actual            │ │
│ │ $450.00                  │ │
│ │ Próximo vencimiento:     │ │
│ │ 1-jul (3 días) ⚠         │ │
│ ╰─────────────────────────╯ │
│ Facturas        Pagos       │
│ ───────         ─────       │
│ • Jun $450 ⚠ Pendiente      │
│ • May $450 ● Pagada         │
│ • Abr $450 ● Pagada         │
│ [ Ver todas ]               │
└─────────────────────────────┘
```
- **Muestra:** adeudo, próximo vencimiento, últimas facturas con estado.
- **Acciones:** tap factura → F-3; pestaña Pagos → F-4.
- **Origen:** ♻️ `account.move` + `om_account_followup`; composición en gateway.

### F-2 · Lista de facturas
```
┌─────────────────────────────┐
│ ←  Mis facturas   Filtrar ▾ │
│ 2026                        │
│ • Jun · $450 · ⚠ Pendiente  │
│ • May · $450 · ● Pagada     │
│ • Abr · $450 · ● Pagada     │
│ • Mar · $450 · ● Pagada     │
│ [ Cargar más ]              │
└─────────────────────────────┘
```
- **Acciones:** filtro (pagada/pendiente/vencida); tap → F-3.

### F-3 · Detalle de factura / CFDI
```
┌─────────────────────────────┐
│ ←  Factura jun-2026         │
│ Folio: A-1234               │
│ Tipo: FACTURA (timbrada) ✅ │
│ Monto: $450.00              │
│ Emitida: 1-jun · Vence:1-jul│
│ Estado: ⚠ Pendiente         │
│ UUID: a1b2…  (verificable)  │
│                             │
│ [ Descargar PDF ]           │
│ [ Descargar XML (CFDI) ]    │
│ [ Pagar* ]                  │  *Fase 2
└─────────────────────────────┘
```
- **Muestra:** datos fiscales, etiqueta FACTURA/REMISIÓN, estatus de timbrado, UUID.
- **Acciones:** descargar PDF / XML. (Pagar = Fase 2.)
- **Origen:** ♻️ render CFDI + helpers timbrado (solo lectura); caché en gateway.

### F-4 · Historial de pagos
```
┌─────────────────────────────┐
│ ←  Mis pagos                │
│ • 2-may $450 · Depósito     │
│ • 1-abr $450 · Transferencia│
│ • 3-mar $450 · Efectivo     │
└─────────────────────────────┘
```
- **Muestra:** pagos aplicados (fecha, monto, forma).

---

# 6. Soporte / Servicios  [Fase 1–2]

### SP-1 · Inicio de soporte (tickets)
```
┌─────────────────────────────┐
│ ←  Soporte                  │
│ [ + Reportar un problema ]  │
│                             │
│ Mis solicitudes             │
│ • OS-0192 · Internet lento  │
│      🚚 Técnico en camino   │
│ • OS-0181 · Revisión panel  │
│      ● Resuelto             │
│ [ Ver historial ]           │
│                             │
│ 💬 ¿Urgente? Chatea por      │
│    WhatsApp                  │
└─────────────────────────────┘
```
- **Muestra:** botón reportar, tickets activos con estado, acceso a WhatsApp.
- **Acciones:** reportar (SP-2) · tap ticket (SP-3) · WhatsApp.

### SP-2 · Reportar un problema
```
┌─────────────────────────────┐
│ ←  Reportar un problema     │
│ ¿Qué servicio?              │
│  ( ) Alarma  ( ) Internet   │
│ Cuéntanos qué pasa:         │
│ ( ____________________ )    │
│ [ 📎 Adjuntar foto* ]       │  *opcional
│ [ ] Es urgente              │
│ [ Enviar ]                  │
└─────────────────────────────┘
```
- **Muestra/Acciones:** servicio + descripción + foto opcional + urgente → crea ticket.
- **Confirmación:** "Listo. Folio OS-0193. Te avisaremos por WhatsApp." → SP-3.
- **Origen:** 🔧 extraer creación de orden a método de modelo; ♻️ `fsm.order`.

### SP-3 · Detalle del ticket (tracker)
```
┌─────────────────────────────┐
│ ←  OS-0192 · Internet lento │
│ Estado:                     │
│ ●──●──●──○                  │
│ Recibido·Asignado·EnCamino  │
│ Técnico: Manuel S.          │
│ ETA: 25 min                 │
│ [ Ver en mapa ]  (SP-4)     │
│                             │
│ Conversación                │
│ • Tú: "Va muy lento"        │
│ • Sentinela: "Vamos para    │
│   allá"                     │
│ ( escribe…        ) [ → ]   │
└─────────────────────────────┘
```
- **Muestra:** stepper de estado, técnico, ETA, chat.
- **Acciones:** ver mapa (SP-4) · chatear.
- **Origen:** ♻️ `fsm.order`, `fsm.chat.message`.

### SP-4 · Rastreo del técnico en vivo
```
┌─────────────────────────────┐
│ ←  Técnico en camino        │
│ ╭─────────────────────────╮ │
│ │   [ mapa con ruta ]      │ │
│ │   🚚 ─ ─ ─→ 🏠           │ │
│ ╰─────────────────────────╯ │
│ Manuel S. · ETA 22 min      │
│ Última ubicación: hace 30 s │
│ [ Llamar al técnico ]       │
└─────────────────────────────┘
```
- **Muestra:** mapa, ETA, última ubicación + timestamp.
- **Estados:** si Traccar no responde → "última ubicación conocida hace X" (degradación elegante, nunca pantalla muda).
- **Origen:** ♻️ `get_last_location_from_traccar`.

### SP-5 · Encuesta de satisfacción (al cerrar)
```
┌─────────────────────────────┐
│  ¿Cómo te atendimos?        │
│  ★ ★ ★ ★ ☆                  │
│  Comentario (opcional)      │
│  ( ____________________ )   │
│  [ Enviar ]                 │
│  ──────────────────────────│
│  🎟️ ¡Gracias! Tu boleto:    │
│     RIF-0457                 │
└─────────────────────────────┘
```
- **Acciones:** calificar + comentar → asigna boleto de rifa.
- **Origen:** ♻️ `register_survey_response`.

---

# 7. Mi Cuenta  [Fase 0–1]

### MC-1 · Inicio de cuenta
```
┌─────────────────────────────┐
│ ←  Mi cuenta                │
│ Carmen García               │
│ +52 868 123 4567            │
│                             │
│ [ Mis datos ]               │
│ [ Mis servicios y contratos]│
│ [ Notificaciones ]          │
│ [ Seguridad y acceso ]      │
│ [ Modo simple ]             │
│ ─────────────────────────── │
│ [ Cerrar sesión ]           │
└─────────────────────────────┘
```

### MC-2 · Mis datos (contacto/fiscal)
```
┌─────────────────────────────┐
│ ←  Mis datos                │
│ Nombre: Carmen García       │
│ WhatsApp: 868••• [editar]   │
│ Correo: (agregar)           │
│ Domicilio de servicio: …    │
│ Datos fiscales (CFDI)       │
│  RFC: GAGC… [editar]        │
│  Uso CFDI / régimen …       │
│ [ Guardar ]                 │
└─────────────────────────────┘
```
- **Origen:** ♻️ `res.partner`. Cambios sensibles (RFC) pueden requerir validación.

### MC-3 · Servicios y contratos
```
┌─────────────────────────────┐
│ ←  Servicios y contratos    │
│ 🛡️ Alarma residencial       │
│    Activo · $450/mes        │
│    Contrato: ✅ Firmado      │
│ 🌐 Internet 45M             │
│    Activo · incluido        │
│    Contrato: 📝 Por firmar  │
│    [ Firmar ahora ]         │
└─────────────────────────────┘
```
- **Acciones:** `Firmar ahora` → flujo de firma (magic link / canvas). ♻️ `sign_document.action_sign`.

### MC-4 · Notificaciones
```
┌─────────────────────────────┐
│ ←  Notificaciones           │
│ Canal preferido             │
│  [x] WhatsApp               │
│  [ ] Push                   │
│  [ ] Correo                 │
│ Avisarme de…                │
│  [x] Eventos de alarma      │
│  [x] Vencimiento de factura │
│  [x] Estado de mis tickets  │
│ [ Guardar ]                 │
└─────────────────────────────┘
```
- **Origen:** ♻️ `partner.notify()` prefs.

### MC-5 · Seguridad y acceso
```
┌─────────────────────────────┐
│ ←  Seguridad y acceso       │
│ [ Cambiar contraseña ]      │
│ [x] Face ID / huella        │
│ Sesiones activas            │
│  • Este teléfono (ahora)    │
│  • iPad · hace 3 días [salir]│
└─────────────────────────────┘
```
- **Acciones:** contraseña, biométrico, cerrar sesiones remotas.

### MC-6 · Sugerencias y comentarios  [Fase 1]
```
┌─────────────────────────────┐
│ ←  Sugerencias y comentarios│
│ Tu opinión nos mejora.      │
│ Tipo:                       │
│  ( ) Sugerencia ( ) Queja   │
│  ( ) Felicitación           │
│ ( ____________________ )    │
│ [ 📎 Adjuntar* ]  [ Enviar ]│
│                             │
│ Enviadas                    │
│ • 02-jun "Más horarios" ✅  │
│   Recibida · Gracias        │
└─────────────────────────────┘
```
- **Muestra/Acciones:** enviar sugerencia/queja/felicitación + adjunto opcional; historial con acuse.
- **Acceso:** desde Mi Cuenta y desde Soporte (SP-1).
- **Origen:** 🆕 modelo ligero `sentinela.suggestion` (ya previsto en PRD §13/§7).

---

# 8. Internet (residencial, si aplica)  [estado Fase 1–2 · consumo/diagnóstico Fase 2]

> Aparece solo si el cliente tiene servicio de internet.

### I-1 · Estado de mi Internet
```
┌─────────────────────────────┐
│ ←  Internet                 │
│ ╭─────────────────────────╮ │
│ │ ● Conectado              │ │
│ │ Plan: 45 Mbps            │ │
│ │ Señal de antena: buena   │ │
│ │ Enlace estable: 6 días   │ │
│ ╰─────────────────────────╯ │
│ [ Probar mi servicio* ]     │  *diagnóstico básico
│ [ Reportar una falla ]      │
│ Consumo (este mes)*         │  *Fase 2
│  ▁▂▄▆▅▃▂  120 GB            │
│ [ Ver historial ]           │
└─────────────────────────────┘
```
- **Muestra:** estado del enlace, plan contratado, calidad de señal (traducida), estabilidad. *(Consumo gráfico = Fase 2, desde TimescaleDB netwatch.)*
- **Acciones:** probar servicio (diagnóstico básico) · reportar falla (→ SP-2) · ver historial (I-2).
- **Origen:** ♻️ `subscription.conn_online/antenna_signal_dbm/live_traffic_status` · 🔧 consumo (netwatch TSDB, Fase 2).

### I-2 · Historial de incidencias y diagnóstico
```
┌─────────────────────────────┐
│ ←  Historial de internet    │
│ Diagnóstico ahora:          │
│ ● Enlace OK · Antena OK     │
│ ● Sin fallas conocidas en   │
│   tu zona                   │  ← Fase 2: status por zona
│ ───────────────────────────│
│ Incidencias                 │
│ • 20-may Corte 35 min       │
│    Causa: energía CFE       │
│ • 02-may Lentitud · resuelto│
└─────────────────────────────┘
```
- **Muestra:** diagnóstico actual (lado Sentinela), historial de cortes/incidencias con causa.
- **Nota:** el **autodiagnóstico "¿soy yo o la red?"** y el **status por zona** completos son **Fase 2** (PRD §8). En v1 se muestra el estado actual y el historial.
- **Origen:** ♻️ estado del enlace · 🔧 historial de cortes + sectores netwatch (Fase 2).

---

# 9. Centro de notificaciones  [Fase 1]

### N-1 · Notificaciones (destino del 🔔)
```
┌─────────────────────────────┐
│ ←  Notificaciones    ✓ Leer │
│ Hoy                         │
│ 🔴 14:32 Evento en tu       │
│    domicilio        [Ver]   │
│ ⚠ 09:00 Factura vence en 3d │
│                     [Ver]   │
│ Antes                       │
│ 🚚 OS-0192 técnico asignado │
│ ✅ OS-0181 servicio cerrado │
│ 🎟️ Boleto de rifa RIF-0457  │
└─────────────────────────────┘
```
- **Muestra:** historial de notificaciones, agrupado por fecha; cada una enlaza a su pantalla (deep-link).
- **Acciones:** marcar leídas · tap → pantalla destino · ⚙️ → preferencias (MC-4).
- **Origen:** 🆕 centro de notificaciones en gateway (push tokens + bandeja); preferencias ♻️ `partner.notify()`.

---

## Mapa de navegación (flujo residencial)

```
Onboarding(O-1)→Login(L-1→L-2→L-3)→Tour(O-2)→Checklist(O-3)→Dashboard(D-1)
Dashboard ──┬─→ 🔔 Notificaciones(N-1)→[deep-link a pantalla destino]
            ├─→ Seguridad(S-1)─┬→Eventos(S-2)→Detalle(S-3)→PDF(S-4)
            │                  ├→Contactos(S-5)
            │                  └→Equipos/Mantenimiento(S-7)
            ├─→ Internet(I-1)→Historial/Diagnóstico(I-2)        (si aplica)
            ├─→ Facturas(F-1)→Lista(F-2)→Detalle/CFDI(F-3) · Pagos(F-4)
            ├─→ Soporte(SP-1)→Reportar(SP-2)→Ticket(SP-3)→Mapa(SP-4)→Encuesta(SP-5)
            └─→ Cuenta(MC-1)→Datos(MC-2)·Contratos(MC-3)·Notif(MC-4)·Seguridad(MC-5)·Sugerencias(MC-6)
Externos (magic link, sin sesión): Autorizar patrulla(S-6) · Firmar contrato(desde MC-3)
```

## Verificación de la regla de las 3 interacciones (desde Dashboard)

| Acción del cliente | Ruta | Taps |
|---|---|---|
| Ver estado del panel | Dashboard→Seguridad | 1 |
| Descargar reporte PDF de evento | Dashboard→Seguridad→Evento→PDF | 3 |
| Ver/descargar factura (CFDI) | Dashboard→Factura(pendiente)→Descargar | 2 |
| Reportar un problema | Dashboard→Reportar→Enviar | 2 |
| Rastrear al técnico | Dashboard→Soporte→Ticket→Mapa | 3 |
| Contactos de emergencia | Dashboard→Seguridad→Contactos | 2 |
| Equipos / próximo mantenimiento | Dashboard→Seguridad→Equipos | 2 |
| Agendar mantenimiento | Dashboard→Seguridad→Equipos→Agendar | 3 |
| Firmar contrato | Dashboard(ámbar)→[Firmar]  ·  o Cuenta→Contratos→Firmar | 1 / 3 |
| Estado de internet | Dashboard→Internet | 1 |
| Llamar a monitoreo | Dashboard→Seguridad→Llamar | 2 |
| Ver notificaciones | Dashboard→🔔 | 1 |
| Enviar sugerencia | Dashboard→Cuenta→Sugerencias | 2 |

✅ Todas las acciones importantes ≤ 3 interacciones.

## Decisiones tomadas (flujo residencial APROBADO)
- ✅ **Equipos (S-7):** Opción A — v1 muestra equipos instalados + condición (propio/comodato/leasing) + datos existentes. Garantía, vida útil y mantenimiento preventivo detallado → fase posterior con modelo específico.
- ✅ **Facturación:** solo acción **"Ver"** en v1. Pagos en línea fuera de alcance hasta su fase.
- ✅ **Modo Vacaciones:** fuera de v1; planificado para fase posterior.
- ✅ **Emergencia / Llamar a Sentinela:** botón persistente incorporado a v1 (cabecera + modo simple).
- ✅ **Selector de domicilio:** incorporado a v1 (cuando hay >1 dirección de servicio).
- ✅ **Checklist de configuración (O-3):** incorporado al onboarding de v1.

> Flujo residencial aprobado por Enrique el 25-jun-2026. Base para diseño visual (Figma).
