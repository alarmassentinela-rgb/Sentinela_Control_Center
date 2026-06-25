# PRD Maestro — Centro de Operaciones del Cliente (COC) · Alarmas Sentinela

> **Documento oficial de especificación funcional.** Base para el desarrollo del proyecto.
> Estado: **Alcance v1 CONGELADO.** Las ideas nuevas se documentan en el Backlog (§13), no alteran v1.
> Versión del documento: 1.0 · Fecha: 2026-06-25 · Autor: Arquitectura (Enrique Garza + Claude)

---

## 1. Resumen ejecutivo

El **Centro de Operaciones del Cliente (COC)** es el canal digital principal de Alarmas Sentinela: un portal (web + futura app móvil) donde cada cliente administra **todos** sus servicios (alarma, internet, GPS, CCTV, acceso, patrullaje, mantenimiento), consulta su **facturación/CFDI**, **reporta y da seguimiento** a soporte, y confirma de un vistazo que **todo está en orden**.

- **No reemplaza Odoo.** Odoo 18 Community sigue siendo el **motor de negocio y la única fuente de verdad**.
- **No duplica lógica ni datos.** El portal **expone y consume** la lógica existente vía una API.
- **Construido para escalar** a miles de clientes y servir de base a la app móvil.
- **Diseñado para evolucionar** a plataforma multiempresa/white-label/SaaS, sin sobrecosto en v1 (ver §12).

---

## 2. Objetivos y métricas de éxito

| Objetivo | Métrica (KPI) | Meta v1 |
|---|---|---|
| Autoservicio | % de consultas (saldo, factura, estado) resueltas sin llamar | ↓ 40% llamadas a oficina |
| Adopción | % de clientes activos que entran ≥1×/mes | ≥ 35% en 6 meses |
| Tranquilidad | % de sesiones que ven "Estado de tranquilidad" verde | medición base |
| Soporte | % de tickets creados desde el portal | ≥ 30% |
| Cobranza | % de facturas consultadas/descargadas desde el portal | ≥ 50% |
| Satisfacción | CSAT post-servicio (encuesta existente) | ≥ 4.3/5 |

---

## 3. Alcance v1 (congelado)

### 3.1 DENTRO de v1 (Must)
- Identidad y acceso: OTP por WhatsApp + usuario/contraseña + biométrico; magic links solo para firma y autorizaciones.
- Dashboard con **Estado de Tranquilidad** (héroe) + latido del panel.
- Mis Servicios (suscripciones/membresías).
- Facturación **solo consulta**: estado de cuenta, facturas/remisiones, CFDI (PDF+XML), historial de pagos, vencimientos, adeudo.
- Seguridad/Alarma: eventos + reporte PDF, contactos de emergencia, autorizar patrulla (magic link), llamar a monitoreo.
- Internet: estado en vivo (enlace/señal/velocidad) + reportar falla.
- GPS/Flotilla: mapa en vivo, lista de unidades, compartir ubicación temporal.
- Soporte/Servicios: crear ticket, **tracking del técnico en vivo**, chat, encuesta + rifa.
- Mi cuenta: perfil, datos fiscales, **firma de contratos**, preferencias de notificación, gestión de sesiones.
- Notificaciones: push + avisos por WhatsApp.
- Costura de branding (theme endpoint) y record rules de seguridad.

### 3.2 FUERA de v1 (derivado a fases posteriores / backlog §13)
- Pagos en línea (Fase 2).
- Consumo histórico de internet + mapa de status por zona (Fase 2 / telemetría).
- Autodiagnóstico "¿soy yo o la red?" (Fase 2).
- Botón SOS, Resumen mensual "Tu mes protegido", inmovilizar vehículo (Fase 2/3).
- Asistente IA conversacional (Fase 4) — en v1 el botón flotante lleva a WhatsApp humano.
- Tiempo real por WebSocket/SSE (v1 usa polling).
- Modo Acompáñame/Guardián, Centro de Mando empresarial, Familia residencial, Referidos, Command palette (Fase 3).
- CCTV y Control de acceso operativos (placeholders visuales en v1; telemetría posterior).
- Capacidades multiempresa / white-label / SaaS (post-producción estable, §12).

---

## 4. Principios de producto y arquitectura

### 4.1 Producto
1. **Tranquilidad primero** — responder "¿está todo bien?" en 1 segundo.
2. **Proactivo, no reactivo** — avisar antes de que el cliente descubra el problema.
3. **Transparencia radical** — ver al técnico/patrullero llegar; descargar el reporte.
4. **Nativo de WhatsApp y móvil** — login, avisos y soporte donde el cliente vive.
5. **Adaptable a quién eres** — residencial simple/emocional vs empresarial denso/operativo.

### 4.2 Arquitectura (aprobada)
- **Híbrida con visión API-first.** 3 capas + gateway:
  - **SPA web (+ móvil futura)** consumen exclusivamente la API.
  - **API Gateway/BFF (FastAPI)**: identidad, JWT, OTP, agregación, caché, orquestación IA/notif. Evoluciona independiente de Odoo.
  - **Addon Odoo `sentinela_api` (REST/JSON)**: serializa y reúsa la lógica de los módulos `sentinela_*`; aplica record rules de partner.
  - **Odoo 18 + módulos `sentinela_*`**: fuente de verdad + integraciones (MikroTik, Traccar/SentiCar, floLIVE, Prodigia, EvoApi).
- **Reutilización máxima**: la lógica ya vive en métodos de modelo; la API **no reescribe**, extrae lo poco atrapado en controllers QWeb.
- **Convivencia**: las vistas QWeb actuales (`/my/*`) siguen vivas durante la migración; se apagan una por una.
- **Single-tenant con costuras** para multiempresa futura (§12).

### 4.3 Identidad y autenticación
- Identidad del cliente vive en el **gateway** (no se crean miles de `res.users`); mapea teléfono/email → `partner_id` de Odoo (reutiliza `find_partner_by_phone`).
- Métodos: usuario+contraseña, **OTP por WhatsApp** (canal transaccional separado del inbox de soporte), biométrico tras primer OTP, recuperación por WhatsApp/email.
- **Magic links** solo para: firma de documentos y autorización de servicios extra.
- JWT con `partner_id` + scopes; scope por cliente validado **también en Odoo** (record rules), no solo en el gateway.

---

## 5. Personas

| | 🏠 Residencial | 🏢 Empresarial |
|---|---|---|
| Servicios | Alarma (± internet) | Internet + Alarma + GPS + CCTV + Acceso, multi-sucursal |
| Uso | Esporádico, móvil, quizá sin email | Diario, escritorio+móvil, varios usuarios/roles |
| Pregunta clave | "¿Mi casa está protegida? ¿Cuánto debo?" | "¿Operan mis servicios? ¿Dónde están mis unidades? ¿Cómo va mi cuenta?" |
| Valora | Simplicidad, tranquilidad, pagar fácil | Control, reportes, multi-usuario/rol, SLA, consolidado |
| Tono | Cálido, tranquilizador | Operativo, eficiente |

**Decisión:** un solo portal **adaptativo por capacidades y perfil**.

---

## 6. Arquitectura de información y navegación

Navegación adaptativa (solo aparecen servicios contratados):

```
🏠 Inicio (Dashboard)        ← siempre
🛡️ Seguridad / Alarma        ← si tiene alarma
🌐 Internet                   ← si tiene internet
📍 GPS / Flotilla             ← si tiene GPS
📹 Cámaras (CCTV)             ← placeholder v1
🚪 Accesos                    ← placeholder v1
🧾 Facturación                ← siempre
🛠️ Soporte / Servicios        ← siempre
💬 Asistente (→WhatsApp v1)   ← siempre, flotante
👤 Mi cuenta                  ← siempre
```
- Residencial: barra inferior con 5 ítems (Inicio · Seguridad · Facturación · Soporte · Mi cuenta).
- Empresarial: navegación completa + selector de **sucursal/sitio** y **usuario/rol** en cabecera.

---

## 7. Especificación por módulo

> Prioridad MoSCoW: **M**ust / **S**hould / **C**ould / **W**on't(v1).
> Backend: ♻️ reusa lo existente · 🔧 requiere refactor/extracción · 🆕 construir.

### 7.1 Inicio / Dashboard — [M · Fase 0–1]
- **Ve:** Estado de Tranquilidad (semáforo agregado de todos los servicios) + latido del panel; tarjetas por servicio activo (estado en vivo + dato clave); pendientes accionables (facturas por vencer, técnico en camino, autorizaciones, contratos por firmar).
- **Acciones:** navegar a cada módulo; resolver pendientes; (residencial) "Reportar problema".
- **Indicadores:** última comunicación del panel, días sin eventos, adeudo, próximo vencimiento, (empresarial) servicios OK/atención/crítico, SLA del mes.
- **Backend:** ♻️ estados de sub, `last_communication`, eventos, account.move. 🆕 composición del "estado de tranquilidad" y health en el gateway.
- **Aceptación:** carga del héroe < 1 s percibido; refleja correctamente verde/ámbar/rojo según señales reales.

### 7.2 Seguridad / Alarma — [M · Fase 2 (núcleo); eventos en Fase 1–2]
- **Ve:** estado del panel (en línea/sin comunicar + "última señal"), historial de eventos (tipo, fecha, zona, **cómo se resolvió**), contactos de emergencia, patrullaje despachado, zonas/particiones.
- **Acciones:** descargar **reporte PDF de incidente**; autorizar servicio extra/patrulla (magic link); actualizar contactos; marcar falsa alarma; llamar a monitoreo (click-to-call).
- **Indicadores:** última comunicación, días sin eventos, tiempo de respuesta del monitoreo (SLA), batería/señal del panel.
- **Backend:** ♻️ `sentinela.alarm.event`, `_render_master_report_pdf`, `service.authorization.token`. 🆕 `get_health_status` del panel.
- **Aceptación:** un cliente solo ve sus eventos (record rule); el PDF se descarga correctamente; autorización con TTL y auditoría.

### 7.3 Internet — [M (estado) · Fase 1–2 ; consumo S · Fase 2]
- **Ve:** estado del enlace, calidad de señal (traducida: buena/regular/débil), velocidad contratada vs real, historial de cortes. *(Consumo gráfico = Fase 2.)*
- **Acciones:** reportar lentitud/caída (genera ticket), ver ticket y técnico en camino. *(Prueba de velocidad y autodiagnóstico = Fase 2.)*
- **Indicadores:** uptime del mes, estabilidad del enlace; *(consumo vs periodo anterior = Fase 2)*.
- **Backend:** ♻️ `subscription.conn_online/antenna_signal_dbm`. 🔧 consumo desde TimescaleDB de netwatch (Fase 2).
- **Aceptación:** estado en vivo correcto; reporte de falla crea ticket scopeado al cliente.

### 7.4 GPS / Flotilla — [M · Fase 2–3]
- **Ve:** mapa en vivo con unidades; lista con estado (en línea/sin reportar/movimiento/detenido), última posición + hora; alertas (geocerca, velocidad).
- **Acciones:** ver recorrido/historial; **compartir ubicación temporal** (link que expira). *(Comandos como inmovilizar = Fase 2/3.)*
- **Indicadores:** unidades reportando/total, alertas activas, km recorridos.
- **Backend:** ♻️ `senticar.service`, `gps_device`, `create_share_link`, `get_last_location_from_traccar`.
- **Aceptación:** mapa refleja posiciones reales; compartir genera link temporal funcional.

### 7.5 Facturación (solo consulta v1) — [M · Fase 1]
- **Ve:** estado de cuenta (saldo, adeudo, vencimientos), facturas/remisiones con estado (pagada/pendiente/vencida), historial de pagos.
- **Acciones:** descargar **PDF + XML (CFDI)**; ver detalle. *(Pagar en línea = Fase 2.)*
- **Indicadores:** adeudo total, próximo vencimiento, alerta de vencida.
- **Empresarial:** estado de cuenta **consolidado** multi-sucursal + descarga masiva de CFDI.
- **Backend:** ♻️ `account.move`, render CFDI, helpers timbrado (solo lectura), `om_account_followup`. 🆕 composición del estado de cuenta.
- **Aceptación:** solo lectura; PDF+XML correctos; cliente solo ve sus facturas (record rule).

### 7.6 Soporte / Servicios — [M · Fase 1–2]
- **Ve:** órdenes de servicio (folio, tipo, estado, técnico), historial, chat.
- **Acciones:** **reportar problema** (→ ticket); **rastrear técnico en vivo** (mapa + ETA); chatear; calificar al cerrar (encuesta + boleto de rifa).
- **Indicadores:** ETA del técnico, estado del ticket en tiempo real, historial.
- **Backend:** ♻️ `sentinela.fsm.order`, tracking JSON, `fsm.chat.message`, `register_survey_response`. 🔧 extraer creación de orden a método de modelo.
- **Aceptación:** tracking muestra última posición + timestamp aunque Traccar falle; ticket scopeado al cliente.

### 7.7 Mi cuenta — [M · Fase 0–1]
- **Ve:** datos de contacto/fiscales; servicios + contratos (firmados/por firmar); preferencias de notificación; seguridad/sesiones.
- **Acciones:** actualizar datos; **firmar contrato** (magic link); gestionar notificaciones; *(empresarial: gestionar usuarios y roles — ver §7.8)*.
- **Backend:** ♻️ `res.partner`, `sign_document.action_sign`, `notify()`.
- **Aceptación:** firma funciona end-to-end; cambios de preferencia se respetan.

### 7.8 Usuarios y roles (empresarial) — [S · Fase 2]
- **Roles v1 propuestos (a confirmar):** Titular (todo), Operador-flotilla (solo GPS), Contador (solo facturación), Lectura/Familiar (solo consulta).
- **Backend:** 🆕 modelo de roles a nivel gateway (scopes en JWT).

### 7.9 Notificaciones — [M · Fase 1]
- **Ve:** centro de notificaciones; preferencias por canal (WhatsApp/push/email).
- **Acciones:** marcar leídas; ajustar canales.
- **Backend:** ♻️ `partner.notify()` multicanal. 🆕 registro de push tokens + centro de notificaciones.

### 7.10 CCTV y Control de acceso — [W(v1) · placeholders visuales]
- v1 muestra la sección como "Próximamente" si el cliente tiene el servicio. Telemetría real en fase posterior (requiere definir fuente de datos NVR/controladora).

### 7.11 Asistente — [S · Fase 4; v1 = enlace a WhatsApp]
- v1: botón flotante → soporte humano por WhatsApp. Fase 4: IA con contexto real de la cuenta + escalamiento.

---

## 8. Funciones diferenciadoras ("firmas")

| Firma | Prioridad | Fase | Backend |
|---|---|---|---|
| Estado de Tranquilidad + latido del panel | M | 1 | ♻️ |
| Tracking del técnico en vivo (estilo Uber) | M | 1–2 | ♻️ |
| Reporte de incidente descargable (PDF) | M | 2 | ♻️ |
| WhatsApp como canal de primera clase (avisos) | M | 1 | ♻️ |
| Status de servicio por zona (transparencia de fallas) | S | 2 | ♻️ (sectores netwatch) |
| Autodiagnóstico "¿soy yo o la red?" | S | 2 | ♻️ |
| Botón SOS / Pánico | S | 2 | ♻️ (crea evento) |
| Resumen mensual "Tu mes protegido" | S | 2 | ♻️ |
| Inmovilizar vehículo (flotilla) | S | 2–3 | ♻️ (comandos SMS GPS) |
| Modo Acompáñame / Guardián | C | 3 | 🆕 |
| Centro de Mando empresarial (wallboard) | C | 3 | ♻️ |
| Familia residencial / Referidos | C | 3 | 🆕 |

---

## 9. Flujos clave (v1)

- **Onboarding:** Bienvenida → "Entra con tu WhatsApp" → teléfono → OTP → (opc. contraseña/biométrico) → tour 3 pasos → Dashboard.
- **Evento de alarma:** Push/WhatsApp → detalle (qué/cuándo/zona) → estado de atención → (si hay patrulla) mapa del patrullero → al cerrar: reporte PDF.
- **Consulta de factura:** Dashboard "vence en 3 días" → detalle → descargar PDF/XML. *(Pago = Fase 2.)*
- **Reportar + seguir técnico:** Soporte "Reportar" → servicio + descripción → folio → "asignado" → "en camino" + mapa + ETA → "en sitio" → "resuelto" → encuesta + boleto.
- **Compartir unidad GPS:** Flotilla → unidad → "Compartir" → link temporal → WhatsApp → expira solo.
- **Autorizar patrulla:** WhatsApp con costo → magic link → autorizar/rechazar → confirmación.

---

## 10. Roadmap de implementación

| Fase | Contenido | Entregable |
|---|---|---|
| **0 — Cimientos** | Bloqueadores de seguridad (record rules en `subscription`/`alarm.event`/`sign.document`); borrar código muerto (`contract_builder`, `syscom.import.queue`); esqueleto `sentinela_api`; gateway con identidad (OTP WhatsApp, JWT); `GET /v1/me`; `GET /v1/config/theme`; SPA shell + login. | Cliente entra con WhatsApp y ve su perfil. |
| **0.5 — Drivers** | Envolver integraciones (MikroTik/Traccar/floLIVE/Prodigia/EvoApi) tras interfaces de adaptador (resiliencia + costura multi-proveedor). | Integraciones con retry/logging, sin `except: pass`. |
| **1 — Consulta** | Dashboard + Estado de Tranquilidad; Mis Servicios; Facturación (consulta); Notificaciones; eventos de alarma (lectura). | El cliente consulta servicios y finanzas. |
| **2 — Operación** | Soporte/tickets + tracking; Seguridad completa (reporte PDF, contactos, autorizar patrulla); Internet (estado + reportar); GPS (mapa/compartir); firmas v2 (SOS, status por zona, autodiagnóstico, resumen mensual). | El cliente opera y se autoservicio. |
| **3 — Telemetría/Avanzado** | Consumo internet; salud de dispositivos; inmovilizar vehículo; Acompáñame; Centro de Mando; familia/referidos. | Indicadores y funciones avanzadas. |
| **4 — Inteligencia** | Asistente IA conversacional; tiempo real (WebSocket/SSE); automatizaciones. | Proactividad + IA. |
| **5 — Expansión** | Pagos en línea; app móvil; CCTV/Acceso operativos; apagado de vistas QWeb antiguas. | Cobertura completa. |

> **Secuencia de deuda técnica aprobada (Opción A):** antes del portal SOLO los bloqueadores de seguridad y borrado de código muerto; el resto (wrappers, split del god-object `subscription.py`, tests) se paga **en paralelo** durante Fases 1–2.

---

## 11. Requisitos no funcionales

- **Rendimiento:** héroe < 1 s percibido; agregación y **caché** en el gateway (PDF/XML y catálogos); nunca N llamadas finas a Odoo por pantalla.
- **Seguridad:** record rules de partner como backstop a nivel datos; JWT corto + refresh; rate-limit en OTP; secretos en `ir.config_parameter`/env/vault; Odoo solo en LAN tras el gateway; logging de acceso al portal.
- **Escalabilidad:** gateway stateless (escala horizontal); Odoo protegido; preparado para miles de clientes.
- **Disponibilidad/resiliencia:** integraciones externas con retry/circuit-breaker; degradación elegante (mostrar última info conocida).
- **Accesibilidad:** móvil-first, alto contraste, tipografía grande, **modo simple** (adultos mayores), modo claro/oscuro.
- **i18n:** español de México; arquitectura lista para más idiomas (costura).
- **Offline/PWA:** resiliente a mala conexión (clientes WISP rurales).
- **Observabilidad:** logs estructurados + métricas en el gateway; trazas request→Odoo.

---

## 12. Costuras para evolución multiempresa (NO se construyen en v1)

Puntos de extensión dejados listos para volver el producto multiempresa/white-label/SaaS sin rehacer arquitectura:
1. **Parámetros de negocio** leídos de un origen de config único (no hardcodeados) → mañana resueltos por inquilino.
2. **Branding** servido por `GET /v1/config/theme` → mañana por hostname.
3. **Integraciones tras interfaz (drivers)** → mañana se elige driver por config.
4. **Backend Odoo leído de config** → mañana un resolver por inquilino.
5. **Identidad/JWT** con estructura lista para un campo `tenant` aditivo.
6. **Capacidades del COC** dirigidas por objeto `capabilities` (todo `on` en Sentinela).
7. **Aislamiento por DB** ya es el patrón (Sentinela = DB `V18` con dbfilter).

Modelo objetivo futuro: **DB por inquilino** (aislamiento físico) + control plane (registro/config/branding) + gateway multi-tenant. **No en v1.**

---

## 13. Backlog de versiones futuras (ideas congeladas fuera de v1)

- Pagos en línea (Stripe/Banorte/HSBC) + conciliación.
- Mapa de status por zona; autodiagnóstico de internet; consumo histórico.
- SOS/Pánico; Modo Acompáñame/Guardián; Modo Vacaciones.
- Resumen mensual "Tu mes protegido" (estilo Wrapped).
- Inmovilizar vehículo; comandos GPS avanzados.
- Asistente IA conversacional; tiempo real WebSocket.
- Centro de Mando empresarial (wallboard); command palette.
- Familia residencial; programa de referidos.
- CCTV y Control de acceso operativos (requiere definir fuente de telemetría).
- Plataforma multiempresa / white-label / SaaS (§12).

---

## 14. Decisiones pendientes de confirmación (no bloquean el inicio)

1. Set final de **roles empresariales** (§7.8).
2. Confirmar las **3 firmas insignia** (Estado de Tranquilidad, SOS+Acompáñame, Status por zona) y su fase exacta.
3. **Nombre del producto** de la plataforma (para el futuro SaaS) — Sentinela como marca del tenant faro.
4. App móvil: nativa vs híbrida (se decide antes de Fase 5).

---

## 15. Referencias

- Auditoría de reutilización por módulo (sesión 25-jun): clasificación 🟢/🟡/🔴 por capacidad.
- Auditoría técnica/funcional + matriz + dependencias + deuda técnica (sesión 25-jun).
- `CLAUDE.md` raíz y por módulo (arquitectura del código).
- Memoria del proyecto: `project_portal_coc.md`.
