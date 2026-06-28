# Producto — Pilar Centro de Soporte y Operaciones

> Documento de PRODUCTO (qué y por qué). Orden: Producto → Procesos → Arquitectura funcional → Tecnología.
> Aplica la regla de las **6 preguntas obligatorias** (§11). Borrador para revisión.

## 0. Visión y objetivos
> **No es un sistema de tickets: es el frente de autoservicio que conecta al cliente con la operación
> real de Sentinela, sin duplicar procesos.**

El cliente debe poder **resolver casi cualquier necesidad desde el Portal** — solicitar
mantenimiento, reportar fallas, solicitar patrulla, dar seguimiento a órdenes e instalaciones,
agendar visitas y comunicarse — y que **todo fluya a la operación existente (FSM/Odoo)**, no a un
sistema paralelo. El cliente expresa una **necesidad** (resultado), no llena un "ticket"; el sistema
la **enruta al proceso operativo correcto** con **transparencia y seguimiento**.

## 1. Problema que resuelve (cliente)
Hoy cualquier necesidad (falla, mantenimiento, visita, patrulla) se gestiona por **teléfono/WhatsApp
manual**, sin **visibilidad del estado** ("¿ya viene el técnico?", "¿en qué va mi orden?"). El
cliente **no tiene control ni seguimiento**, y Sentinela recibe la carga por canales no estructurados.

## 2. Valor para el cliente
**Resolver desde el Portal** sin llamar, con **seguimiento en tiempo real** de su orden/visita,
agenda clara y comunicación trazable. Sensación de control y servicio.

## 3. Valor para Alarmas Sentinela
**Descarga operación** (menos teléfono/WhatsApp no estructurado), **estructura la demanda** (entra
ya como orden bien formada a FSM), **reduce errores y retrabajo**, da **trazabilidad** y libera al
equipo para resolver, no para capturar. **Reutiliza la operación existente** (FSM, el bot
WhatsApp→orden ya hace este patrón) — **sin duplicar procesos**.

## 4. Alcance del pilar (orientado a la necesidad, no al "ticket")
Solicitar mantenimiento · Reportar fallas · Solicitar patrulla · Seguimiento de órdenes ·
Seguimiento de instalaciones · Agenda de visitas (confirmar/reagendar) · Comunicación con Sentinela ·
Evidencias y cierre.
> "Ticket" es solo **uno de los mecanismos** internos; el producto es **autoservicio orientado a
> resolver la necesidad** y enrutarla al proceso operativo adecuado.

## 5. Principio: no duplicar la operación
La operación **vive en FSM/Odoo** (órdenes, visitas, técnicos, despacho). El Portal es el **frente
del cliente**: crea/observa órdenes reales y muestra su estado. **Cero proceso paralelo.** Todo lo
relevante (solicitud creada, orden asignada, visita agendada, atendida, resuelta) **se registra como
evento** en la Plataforma de Eventos → seguimiento, notificaciones y timeline salen de ahí.

## 6. Relación con otros pilares (evitar solapamiento)
- **Solicitar patrulla** existe también en **Seguridad en Vivo**: es **el mismo proceso operativo y el
  mismo evento** (un solo despacho), accesible desde ambos contextos. No se duplica la lógica.
- **SentiAI** puede **abrir y dar seguimiento** a solicitudes en nombre del cliente (consume este pilar).
- **Cobranza:** dudas/solicitudes financieras pueden originar una solicitud o resolverse con SentiAI.

## 7. Flujos
### 7.1 Usuario
Expresa una **necesidad** (reportar falla / pedir mantenimiento / patrulla / agendar) → el Portal la
**convierte en una orden** y muestra su **estado y agenda** → el cliente **da seguimiento, se
comunica y confirma/reagenda** → ve el **cierre y la evidencia**.
### 7.2 Operativo / interno
La solicitud **entra a FSM** como orden estructurada (tipo, servicio, prioridad, dirección) →
operación la atiende en su flujo actual → cada cambio de estado **publica un evento** → el cliente lo
ve en su Timeline y recibe notificación. **El backend operativo no cambia; gana un frente digital.**

## 8. Riesgos
- **Doble entrada** (Portal + WhatsApp/teléfono) durante la transición → consolidar y reflejar todo en FSM.
- **Expectativa de tiempos** (agenda) que la operación no pueda cumplir → comunicar ventanas realistas.
- **Solapamiento de "patrulla"** entre pilares → garantizar un solo proceso/evento.
- **Sobre-carga** si se abren solicitudes triviales → autoayuda + IA de triage.
- **Privacidad** de evidencias (alinear con PROD_03 §9).

## 9. MVP — "Reportar y dar seguimiento"
- **Reportar falla / solicitar servicio** → crea **orden en FSM** (reutiliza el patrón WhatsApp→orden existente).
- **Seguimiento del estado** de la orden (consume eventos de FSM) + **notificación** de cambios.
- **Comunicación básica** asociada a la orden.
- Convive con los canales actuales (transición).

## 10. Evolución
- **V2 — "Agenda y resuelve":** agenda de visitas (ventanas, confirmar/reagendar) + seguimiento de
  instalaciones + **solicitar patrulla integrado** + comunicación bidireccional (chat de la orden) + evidencias y cierre.
- **V3 — "Operación inteligente":** **triage con SentiAI** y auto-enrutamiento + base de conocimiento/
  autoayuda + mantenimiento **preventivo/predictivo** + automatizaciones operativas.

## 11. Las 6 preguntas obligatorias
1. **Problema del cliente:** gestiona todo por canales no estructurados, sin visibilidad ni seguimiento (§1).
2. **Valor Sentinela:** descarga y estructura la operación, trazabilidad, menos retrabajo, reutiliza FSM (§3).
3. **Indicadores:** §12.
4. **MVP:** reportar/solicitar → orden FSM + seguimiento + notificación (§9).
5. **Evolución 24m:** V2 agenda/patrulla/comunicación; V3 triage IA + preventivo (§10).
6. **Integración con la Plataforma de Eventos:** cada cambio de la orden es un evento; seguimiento/notificación/timeline salen de ahí (§5/§7).

## 12. KPIs
% de solicitudes iniciadas en el Portal (vs teléfono/WhatsApp) · % resueltas sin llamada · tiempo de
atención/resolución · cumplimiento de agenda (visitas a tiempo) · reapertura/retrabajo · satisfacción
(CSAT) · carga operativa desviada (horas).

## 13. Línea Base Operativa (PENDIENTE — datos reales post-Go-Live)
| Métrica base | Valor (pendiente) |
|---|---|
| Solicitudes/mes por teléfono/WhatsApp (falla/mantenimiento/visita/patrulla) | _por capturar_ |
| Tiempo promedio de atención/resolución actual | _por capturar_ |
| % de visitas reagendadas / incumplidas | _por capturar_ |

---
**Estado:** **artefacto oficial** (mapa de producto cerrado). No es "sección de tickets": es
"**pido lo que necesito**" desde el contexto/SentiBot (ver PROD_00). Criterio: existe para **resolver
con el menor esfuerzo**. Definiciones de DETALLE para la fase de diseño/arquitectura: (a) tipos de
solicitud del MVP; (b) agenda de visitas en MVP o V2; (c) "solicitar patrulla" como **un solo
proceso/evento** compartido con Seguridad; (d) nivel de comunicación (chat) por orden.
