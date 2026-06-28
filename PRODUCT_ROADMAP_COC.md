# Product Roadmap — Portal del Cliente (COC) · Horizonte 24 meses

> Estrategia de producto, no lista de features. Documento vivo; base para decidir Sprint 2+.
> Construido sobre plataforma consolidada (Sprint 1) y el ecosistema Sentinela existente
> (Odoo: subscriptions/monitoring/fsm/cfdi/digital_sign/sentinela_api; SentiCar/Traccar; Chatwoot;
> EvoApi WhatsApp; netwatch; floLIVE). Sin tocar STAGING del Sprint 1.

## 1. Visión a 2 años
> **De "portal de consulta" a "centro de autogestión y confianza 24/7" del ecosistema Sentinela.**

En 24 meses el COC es el lugar único donde cualquier cliente (alarma, internet, GPS) **ve su
protección en tiempo real, paga y administra su cuenta sin llamar, y recibe soporte asistido por
IA**; y donde Sentinela **reduce costo operativo, baja la morosidad y abre nuevas líneas de
negocio** (upsell, portal de distribuidores, white-label). El portal deja de ser un costo de TI
para volverse **motor de retención, cobranza y crecimiento** — y una ventaja competitiva frente a
WISPs y centrales de monitoreo que aún operan por teléfono/WhatsApp manual.

Norte de cada decisión: *¿esto hace al portal un mejor producto para el cliente y para Sentinela?*

## 2. Principios de producto
- **Autoservicio primero:** cada interacción que hoy pasa por teléfono/WhatsApp manual debe poder resolverse sola en el portal.
- **Confianza visible:** la seguridad (alarma/GPS) es el corazón emocional; mostrarla en vivo es el diferenciador.
- **Reutiliza el ecosistema:** casi todo el backend ya existe en Odoo/SentiCar/Chatwoot; el COC los **expone y orquesta**, no los reinventa.
- **Valor medible:** cada iniciativa nace con su métrica (conversión de pago, tickets desviados, morosidad, adopción).

## 3. Pilares e iniciativas
Flags: 🏆 alto ROI · ⭐ diferenciador competitivo · 💰 potencial nueva línea de negocio.
Impacto (B/M/A) y Esfuerzo (B/M/A) son de producto (impacto de negocio vs costo total), no solo técnico.

### Pilar A — Cobranza y Finanzas
| Iniciativa | Problema de negocio | Valor cliente | Valor Sentinela | Imp/Esf | Flags |
|---|---|---|---|---|---|
| Pagos en línea (pasarela) | Cobranza lenta, depende de OXXO/banco | Paga en 2 toques | Acelera flujo, baja morosidad | A / B | 🏆 |
| Pago recurrente / tarjeta en archivo | Morosidad recurrente, reintentos manuales | "Olvídate de pagar" | Cobro automático, menos cartera vencida | A / M | 🏆 |
| Autofacturación CFDI (cliente timbra) | Timbrado manual consume operación | Factura cuando quiera | Menos trabajo de facturación | A / M | 🏆 |
| Recordatorios y pronto-pago | Olvidos de pago | Avisos útiles + descuento | Cobranza preventiva | M / B | 🏆 |

### Pilar B — Seguridad y Monitoreo (corazón del producto)
| Iniciativa | Problema | Valor cliente | Valor Sentinela | Imp/Esf | Flags |
|---|---|---|---|---|---|
| Estado de alarma en vivo (armado/eventos/particiones) | Cliente no "ve" su seguridad | Tranquilidad visible 24/7 | Diferenciador, menos llamadas "¿está armado?" | A / A | ⭐ |
| Historial/bitácora de eventos | Falta transparencia | Auditoría de su seguridad | Menos disputas, confianza | M / M | ⭐ |
| GPS en vivo (SentiCar) en el portal | App aparte, fricción | Rastreo unificado | Cross-sell GPS, retención | A / M | ⭐ |
| Despacho/seguimiento de patrulla | Cliente no sabe estado del evento | Ve la patrulla en camino | Confianza, diferenciador | M / M | ⭐ |
| Verificación con palabra clave en portal | Identidad ante evento | Seguridad reforzada | Menos falsas | B / B | ⭐ |

### Pilar C — Plataforma de Eventos y Notificaciones (CIMIENTO transversal)
> No es un "módulo de notificaciones": es la **fuente única de eventos** del ecosistema. Suscripciones
> ya produce eventos de cobranza → se **reutilizan**, no se duplican. Detalle: `producto/PROD_02_plataforma_eventos.md`.
| Iniciativa | Problema | Valor cliente | Valor Sentinela | Imp/Esf | Flags |
|---|---|---|---|---|---|
| Núcleo: catálogo + registro único de eventos + enrutamiento | Lógica de avisos acoplada/duplicada por módulo | — | **Una sola fuente de verdad**; cada módulo solo publica | A / M | 🏆 |
| Centro de Notificaciones del Portal (1er consumidor) | Información dispersa, sin historial | Todo en un lugar | Trazabilidad, menos llamadas | A / M | 🏆 |
| Consumidores: correo (reusa Suscripciones) · WhatsApp · push | Comunicación reactiva/incompleta | Enterado por su canal | Omnicanal sin reescribir lógica | A / M | 🏆 |
| Preferencias por evento/canal | Ruido/canal equivocado | Control, sin spam | Mejor entregabilidad | B / B | |

### Pilar D — Experiencia del Cliente
| Iniciativa | Problema | Valor cliente | Valor Sentinela | Imp/Esf | Flags |
|---|---|---|---|---|---|
| Perfil / autogestión (datos, contactos, preferencias) | Cambios por teléfono | Actualiza solo | Menos captura manual | M / B | 🏆 |
| Multi-servicio / multi-sucursal (empresarial) | Clientes con varios sitios | Vista consolidada | Atiende cuentas grandes | M / M | ⭐ |
| Onboarding y firma digital de contrato | Alta lenta en papel | Activa en minutos | Acelera ventas (digital_sign existe) | M / M | 🏆 |
| App nativa (hoy PWA) | Alcance móvil | Mejor UX/push | Marca en el teléfono | M / A | |

### Pilar E — Soporte y Automatización Operativa
| Iniciativa | Problema | Valor cliente | Valor Sentinela | Imp/Esf | Flags |
|---|---|---|---|---|---|
| Soporte / Tickets (reportar falla → orden FSM) | Soporte por WhatsApp/teléfono saturado | Reporta y da seguimiento | **Descarga operación** (reusa Chatwoot+FSM) | A / M | 🏆 |
| Autogestión de suspensión/reactivación y cambios de plan | Gestiones manuales WISP | Control inmediato | Menos tickets de provisioning | M / M | 🏆 |
| Base de conocimiento / autoayuda | Dudas repetitivas | Resuelve solo | Deflecta soporte | B / B | |

### Pilar F — Inteligencia Artificial
| Iniciativa | Problema | Valor cliente | Valor Sentinela | Imp/Esf | Flags |
|---|---|---|---|---|---|
| Asistente IA en portal (cuenta/pagos/triage) | Soporte 24/7 costoso | Respuestas al instante | Deflecta carga (reusa OpenClaw/SentiAI/Chatwoot) | A / M | ⭐ |
| IA de cobranza (predicción morosidad + mensaje personalizado) | Cartera vencida | Trato relevante | Menos morosidad | A / A | 🏆⭐ |
| IA proactiva (anomalías de alarma/consumo) | Reacción tardía | Aviso temprano | Servicio premium, upsell | A / A | ⭐💰 |

### Pilar G — Analítica
| Iniciativa | Problema | Valor cliente | Valor Sentinela | Imp/Esf | Flags |
|---|---|---|---|---|---|
| Métricas de producto (adopción, conversión, deflexión, churn) | Decidir por percepción | — | Prioriza por uso real | M / B | 🏆 |
| Analítica al cliente (consumo internet, tendencias de eventos, reportes GPS) | Falta de insight | Entiende su servicio | Valor percibido, upsell | M / M | ⭐ |

### Pilar H — Ecosistema Sentinela (plataforma y nuevas líneas)
| Iniciativa | Problema | Valor cliente | Valor Sentinela | Imp/Esf | Flags |
|---|---|---|---|---|---|
| Marketplace / upsell (alarma↔internet↔GPS) | Cliente mono-servicio | Descubre servicios | **Cross-sell**, ARPU | A / M | 🏆💰 |
| Portal de distribuidores/resellers | Reseller GPS sin herramienta | — | Escala canal (SentiCar reseller existe) | M / A | 💰 |
| Referidos | Crecimiento orgánico | Recompensa | Adquisición barata | B / M | 💰 |
| **White-label SaaS** (vender el portal a otros WISP/centrales) | Otros operan manual | — | **Nueva línea de ingresos** (la arquitectura ya es white-label) | A / A | 💰⭐ |
| Tienda de equipo (catálogo Syscom) | Venta de hardware offline | Compra cámaras/sensores | Ingreso adicional | M / M | 💰 |

## 4. Matriz Impacto vs Esfuerzo
- **Quick wins (Imp A / Esf B) — primero:** Pagos en línea · Perfil/autogestión · Recordatorios · Métricas de producto.
- **Big bets (Imp A / Esf A-M) — apuestas:** Seguridad en vivo · IA de cobranza · IA proactiva · White-label · Marketplace/upsell.
- **Rellenos (Imp M / Esf B):** Preferencias de notificación · Verificación con palabra clave · Base de conocimiento.
- **Evitar/aplazar:** App nativa (PWA basta por ahora) · Video/cámaras (hasta que haya demanda e integración NVR).

## 5. Horizontes (24 meses)
**H1 · 0–6 m (Sprint 2–3) — "Cobrar, avisar, autogestionar".** Pagos en línea → Notificaciones core → Perfil/autogestión → Soporte/Tickets MVP.
*Por qué:* ROI inmediato (cobranza), alivio operativo y retención; cimientos (pagos, eventos/notif) de los que dependen pilares posteriores.

**H2 · 6–12 m (Sprint 4–6) — "Ver mi seguridad + cuenta inteligente".** Seguridad en vivo (alarma + GPS) → Pago recurrente → Autofacturación CFDI → Asistente IA v1 → Analítica al cliente.
*Por qué:* diferenciación competitiva y autogestión profunda; el asistente IA ya tiene datos que exponer.

**H3 · 12–18 m — "Inteligencia y crecimiento".** IA de cobranza → IA proactiva (anomalías) → Automatización operativa profunda → Marketplace/upsell → Analítica de negocio.
*Por qué:* convertir datos en menos morosidad, más ARPU y menos operación.

**H4 · 18–24 m — "Plataforma como negocio".** Portal de distribuidores → **White-label SaaS** → Referidos → Tienda de equipo.
*Por qué:* el portal maduro se vuelve producto vendible y canal de nuevas líneas.

## 6. Dependencias y paralelización
- **Cimiento transversal:** un **servicio de eventos/notificaciones** (H1) alimenta seguridad en vivo, cobranza, IA y analítica → priorizarlo temprano.
- **Pagos** habilita pago recurrente, autofactura y cobranza IA.
- **Exponer monitoring/SentiCar por API** habilita seguridad en vivo, IA proactiva y analítica.
- **Paralelizables desde H1:** Cobranza (Pilar A) ∥ Notificaciones (C) ∥ Perfil (D) ∥ Soporte (E) — backends distintos, poco acoplamiento.
- **IA (F)** depende de que monitoring/billing estén expuestos → llega tras H1/H2.
- **Ecosistema (H)** depende de madurez de plataforma → H4.

## 7. Máximo ROI · Diferenciadores · Nuevas líneas
- **Mayor ROI:** Pagos en línea, Pago recurrente, Autofacturación, IA de cobranza, Soporte/Tickets, Marketplace/upsell.
- **Diferenciadores competitivos:** Seguridad en vivo (alarma+GPS), IA proactiva, despacho de patrulla visible, asistente IA.
- **Nuevas líneas de negocio:** White-label SaaS, portal de distribuidores, marketplace/upsell, tienda de equipo, referidos.

## 8. Métricas de éxito por horizonte
- H1: % pagos por portal, morosidad, tickets entrantes desviados, adopción (MAU/clientes).
- H2: uso de "estado en vivo", conversión a pago recurrente, % autofacturas, deflexión por IA.
- H3: reducción de morosidad por IA, ARPU por upsell, % operación automatizada.
- H4: clientes white-label / distribuidores activos, ingresos de nuevas líneas.

## 9. Recomendación para Sprint 2
**Pagos en línea + Notificaciones core + Perfil/autogestión.** Máximo ROI con mínimo riesgo: la UX de pago ya existe (solo conectar pasarela), las notificaciones son el cimiento transversal, y el perfil es un quick win que descarga operación. Antes de Sprint 2: decidir pasarela (Conekta/Stripe/Banorte/HSBC) — investigación pendiente de aprobación.
