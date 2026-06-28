# Producto — Plataforma de Eventos y Notificaciones (corazón del ecosistema Sentinela)

> Documento de PRODUCTO (qué y por qué). Orden: Producto → Procesos → Arquitectura funcional → Tecnología.
> **Dependencia transversal** de Cobranza, Seguridad/Monitoreo, Soporte, IA, GPS, Alarmas, Internet y
> de cualquier módulo futuro. Principio rector: **un evento se define una sola vez; todos los canales
> y módulos lo reutilizan.** No se duplica lógica que ya existe (Suscripciones ya emite eventos de cobranza).

## 0. Visión del pilar — sistema nervioso y MEMORIA HISTÓRICA de Sentinela
> **Fuente ÚNICA de verdad de todo evento relevante del cliente, y memoria histórica del ecosistema.**

Dos roles, ambos estratégicos:
1. **Sistema nervioso (tiempo real):** cualquier hecho de negocio se **publica una vez** y múltiples
   **consumidores** lo reutilizan (Portal, WhatsApp, correo, push, IA, CRM, reportes, dashboards,
   automatizaciones, auditoría). La lógica vive una sola vez; los canales solo "se suscriben".
2. **Memoria histórica (activo estratégico):** **todo lo importante que le ocurre a un cliente existe
   PRIMERO como un evento.** El registro de eventos es la **bitácora histórica** del ecosistema. En
   consecuencia, **la IA del futuro no consultará 20 módulos: consultará el historial de eventos.**
   Lo mismo harán los **dashboards, reportes, automatizaciones y la auditoría.**

> Por eso esta plataforma es uno de los **activos estratégicos más importantes** de Sentinela: quien
> tiene la historia unificada del cliente puede automatizar, predecir y personalizar todo lo demás.

## 1. Problema que resuelve
La lógica de avisos hoy vive **acoplada y parcial** (Suscripciones ya decide y **envía correos** de
cobranza), y cada módulo nuevo tendería a **reimplementar** su mensajería → **duplicación,
inconsistencia entre canales, sin historial unificado y sin un centro de notificaciones**. Además,
**no existe una memoria única** del cliente: hoy su historia está repartida entre módulos, lo que
encarece IA, reportes y auditoría.

## 2. Valor para el cliente
Enterado **a tiempo y por su canal preferido**, un **Timeline único** de todo lo que pasa con sus
servicios (con historial y acciones rápidas), **sin spam** (preferencias por criticidad/canal) y
consistencia omnicanal.

## 3. Valor para Alarmas Sentinela
**Lógica de eventos una sola vez** (no se duplica), **omnicanal** sin reescribir mensajería por
módulo (**menor time-to-market**), **menos llamadas**, y —lo más valioso a largo plazo— una
**memoria histórica unificada** que habilita IA, CRM, dashboards, reportes, automatización y
auditoría **desde una sola fuente**.

## 4. Alcance del pilar
Catálogo y **clasificación por criticidad** de eventos · Productores · **Registro/memoria histórica
única** · Enrutamiento + Preferencias (por criticidad y canal) · **Timeline (Centro de
Notificaciones)** del Portal · Consumidores (Portal, WhatsApp, correo, push, IA, CRM, reportes,
dashboards, automatizaciones, auditoría).

## 5. Clasificación de eventos (por criticidad) — decisión de negocio
La plataforma marca cada tipo de evento como **Obligatorio · Configurable · Informativo**. Además se
distingue **evento obligatorio** (siempre se registra y notifica) de **canal obligatorio** (el canal
puede depender de la preferencia del cliente, **salvo obligación legal/contractual**, que fuerza el canal).

**Críticos / Obligatorios (no desactivables):** Intrusión/alarma · Incendio · Pánico · Patrulla
despachada · Servicio suspendido · Pago confirmado · Pago rechazado · Cargo recurrente rechazado.
*Siempre generan notificación.*

**Importantes / Configurables (el cliente elige canal):** Factura generada · Factura próxima a
vencer · Próximo cargo · Ticket actualizado · Mantenimiento programado · GPS fuera de línea ·
Internet fuera de línea.

**Informativos / Opcionales:** Bienvenida · Novedades · Promociones · Nuevos servicios ·
Recomendaciones de IA.

> Toda preferencia se maneja **por criticidad** (no por módulo): los críticos no se desactivan; en
> los configurables el cliente decide el/los canal(es); los informativos son opt-in.

## 6. Centro de Notificaciones = Timeline del cliente
No es una lista: es una **cronología completa** de **todos** los eventos del ecosistema del cliente.
- **Filtros (evolución):** Cobranza · Alarmas · GPS · Internet · Soporte · Administración · IA.
- **Acciones rápidas** en eventos accionables: Pagar · Ver factura · Abrir servicio · Ver ubicación ·
  Abrir ticket · Confirmar mantenimiento.
- El Timeline es **completo** (todo queda registrado); los accionables solo añaden el atajo.

## 7. Flujos
### 7.1 Usuario
Recibe la notificación por su canal (según criticidad/preferencia) → la ve en el **Timeline** del
Portal (historial, leído/no leído, filtros) → ejecuta **acción rápida** si aplica → ajusta
**preferencias** (canal por evento configurable).
### 7.2 Operativo / interno
Un módulo **publica** un evento (no decide canales) → la plataforma lo **registra en la memoria
histórica** → **enruta** según **criticidad + preferencias** (respetando canales obligatorios
legales/contractuales) → cada consumidor **entrega/usa** el evento. Las reglas de "cuándo se genera"
viven en el módulo dueño; la plataforma **registra y distribuye**.

## 8. Arquitectura funcional (sin tecnología)
| Bloque | Responsabilidad |
|---|---|
| **Catálogo de tipos** | Definición canónica de cada evento + su **criticidad** (obligatorio/configurable/informativo) y **canales obligatorios** (legal/contractual). |
| **Productores** | Módulos que publican (Suscripciones, Cobranza, Monitoreo, FSM, SentiCar, Netwatch, Soporte…). No conocen canales. |
| **Registro de eventos = MEMORIA HISTÓRICA** | **Fuente única de verdad** + bitácora inmutable/consultable de toda la vida del cliente. |
| **Enrutamiento + Preferencias** | Por **criticidad** y preferencia de canal del cliente; respeta canales obligatorios. |
| **Timeline (Centro de Notificaciones)** | Cronología completa + filtros + acciones rápidas (primer consumidor). |
| **Consumidores** | Portal · WhatsApp · correo · push · **IA · CRM · reportes · dashboards · automatizaciones · auditoría**. No conocen al productor. |

**Desacople total:** el productor no conoce el canal; el consumidor no conoce el módulo; todo pasa
por el evento. Agregar canal/módulo/consumidor = sumar pieza **sin tocar el resto** (mismo principio
que el "motor de pago" de Cobranza). **El historial de eventos es la interfaz que consultarán IA,
dashboards, reportes y auditoría — no los módulos individuales.**

## 9. Dependencias
- **Suscripciones ya produce** eventos de cobranza → primer productor (se **reutiliza**).
- Canales existentes (correo, WhatsApp) → se incorporan como consumidores.
- Timeline del Portal = consumidor nuevo que lee la memoria histórica.

## 10. Migración (incremental, sin lógica duplicada)
El **productor de eventos se vuelve el origen único**. Los correos actuales de Suscripciones pasan a
**consumir** esos eventos. Migración por fases: **(1) convivir** (la plataforma registra los eventos
y aparece el Timeline, los correos siguen) → **(2) trasladar** cada correo a consumir el evento →
**(3) apagar** el flujo anterior. **Nunca dos lógicas permanentes.**

## 11. Riesgos
Doble envío en transición (mitiga la migración por fases) · ruido/spam (mitiga la clasificación por
criticidad + preferencias) · duplicación/orden de eventos (idempotencia/orden a nivel diseño
técnico) · privacidad · acoplar la plataforma a un módulo (mitiga la definición canónica del evento).

## 12. MVP
- **Catálogo + criticidad** inicial = eventos de **cobranza que Suscripciones ya produce** (factura
  creada/próxima a vencer/suspendido/reactivado) + **pago recibido/rechazado** (del MVP de Cobranza).
- **Registro = memoria histórica** de esos eventos (fuente única + historial).
- **Timeline en el Portal** (primer consumidor) + el **canal existente** (correo/WhatsApp) reutilizando
  los eventos que ya produce Suscripciones — **sin duplicar lógica**.
- **Preferencias por criticidad** (críticos fijos; configurables por canal).
- Convive con los correos actuales (fase 1 de la migración).

## 13. Evolución
- **V2:** más productores (alarma, GPS, internet, tickets, mantenimiento) + **push** + filtros del
  Timeline + acciones rápidas completas + preferencias finas + fase 2/3 de migración (apagar correos viejos).
- **V3:** **IA sobre el historial de eventos** (resumen, priorización, recomendaciones), **CRM /
  dashboards / reportes / automatizaciones / auditoría** consumiendo la memoria histórica, agrupación
  anti-spam inteligente.

## 14. KPIs
Cobertura (eventos publicados / módulos que publican) · entrega y lectura por canal · opt-out por
evento configurable · reducción de llamadas · **% de la historia del cliente que vive como evento**
(memoria) · nº de consumidores sobre la plataforma · tiempo de integrar un módulo nuevo · satisfacción.

## 15. Línea Base Operativa (PENDIENTE — datos reales post-Go-Live)
| Métrica base | Valor (pendiente) |
|---|---|
| Correos de cobranza enviados / mes (hoy, Suscripciones) | _por capturar_ |
| Llamadas/contactos por avisos no recibidos | _por capturar_ |
| Canales actuales y alcance | _por capturar_ |

## 16. Impacto en el roadmap
Pasa a ser **cimiento de H1** y **activo estratégico permanente**: dependencia transversal de
Cobranza, Seguridad, Soporte, GPS, Internet e IA. Se construye el **núcleo** (catálogo + criticidad +
memoria histórica + enrutamiento + Timeline) primero; luego se suman **consumidores** (push, IA, CRM,
dashboards, automatizaciones, auditoría) y **productores** (alarma, GPS, internet, tickets) de forma incremental.

---
**Estado:** definiciones de negocio cerradas (clasificación por criticidad §5, Timeline §6, migración
incremental §10, evento/canal obligatorio §5) + visión de memoria histórica (§0/§8). **Artefacto
oficial del Pilar de Plataforma de Eventos y Notificaciones.** Siguiente: **diseño técnico conjunto
Cobranza + Plataforma de Eventos + Stripe**, manteniendo producto y tecnología desacoplados.
