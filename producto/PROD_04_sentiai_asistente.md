# Producto — Pilar Asistente IA del Cliente (SentiAI)

> Documento de PRODUCTO (qué y por qué). Orden: Producto → Procesos → Arquitectura funcional → Tecnología.
> Aplica la regla de las **6 preguntas obligatorias** (§12). Borrador para revisión.

## 0. Visión y objetivos
> **SentiAI no es un chatbot: es la interfaz inteligente del Portal** — un **agente** que conoce todo
> el contexto del cliente y actúa como **asesor de seguridad, financiero y de soporte**.

Es la **materialización del activo estratégico** definido en la Plataforma de Eventos: *"la IA del
futuro no consultará 20 módulos, consultará el historial de eventos"*. SentiAI **consume la memoria
histórica + el estado en vivo + las capacidades de los tres pilares** y convierte el Portal de
"pantallas que navegas" a "un asesor con el que hablas". Objetivos:
1. **Resolver con lenguaje natural** lo que hoy requiere navegar o llamar.
2. **Asesorar** (no solo responder): explicar, recomendar y anticipar.
3. **Actuar** (con barreras): ejecutar acciones de los pilares bajo confirmación y reglas.

## 1. Problema que resuelve (cliente)
El cliente tiene que **saber dónde buscar** (facturas, eventos, servicios) y **cuándo llamar**. No
todos entienden su estado de cuenta, sus eventos de seguridad o por qué se suspendió un servicio.
La información existe, pero **falta quien la interprete y actúe por él**.

## 2. Valor para el cliente
Un **asesor 24/7** que entiende su situación: "¿cuánto debo y por qué?", "¿está protegida mi casa?",
"¿qué pasó anoche?", "paga mi factura", "manda una patrulla", "¿por qué se suspendió mi internet?".
Respuestas claras + acciones, en su idioma, sin navegar ni esperar a un humano.

## 3. Valor para Alarmas Sentinela
**Deflecta carga operativa** (resuelve dudas y trámites sin humano), **acelera cobranza y
autogestión**, **mejora la experiencia** (interfaz conversacional), **personaliza** (upsell/retención
con recomendaciones), y **capitaliza la memoria de eventos** como ventaja competitiva. Reutiliza los
bots existentes (OpenClaw, SentiAI Telegram, Chatwoot) **consolidados y aterrizados en datos reales**.

## 4. Alcance del pilar (tres roles del asesor)
- **Asesor de Seguridad:** explica el estado de protección y los eventos, recomienda (p. ej. "batería
  baja, agenda revisión"), guía en un evento, resume "¿qué pasó esta semana?".
- **Asesor Financiero:** explica facturas/cargos, ayuda a pagar, recuerda, proyecta gasto, sugiere domiciliación.
- **Asesor de Soporte:** resuelve dudas, abre y da seguimiento a solicitudes, agenda visitas.
Transversal: conversacional (texto/voz), **con contexto completo del cliente**, **accionable** (con
confirmación), **proactivo** (resúmenes, alertas inteligentes, recomendaciones) y **omnicanal**
(Portal + WhatsApp), con **barreras de seguridad** (qué hace solo vs requiere confirmación o humano).

## 5. Principio: grounded en datos reales (no inventa)
SentiAI **siempre se fundamenta en la información real** del cliente (memoria de eventos + estado en
vivo + datos de los pilares). En contexto de seguridad y dinero, **nunca debe inventar**: si no sabe
o no tiene certeza, lo dice y **escala a un humano**. La IA **interpreta y actúa sobre datos
verificables**, no genera afirmaciones libres.

## 6. Integración con los pilares y la Plataforma de Eventos
- **Consume** la **memoria histórica** (PROD_02) como su fuente de contexto principal + el **estado en
  vivo** (Seguridad) + datos de **Cobranza**.
- **Actúa** invocando capacidades de los pilares: pagar (Cobranza), solicitar patrulla (Seguridad),
  abrir solicitud/agendar (Soporte) — siempre **con confirmación** y respetando las reglas de cada pilar.
- **Produce eventos** (interacción, recomendación, acción ejecutada) → quedan en la memoria/timeline
  y alimentan analítica. SentiAI **no duplica lógica**: orquesta los pilares existentes.

## 7. Riesgos
- **Alucinación / dato incorrecto** en contexto crítico (dinero/seguridad) → grounding estricto + "no
  sé / te conecto con un humano".
- **Acciones sensibles** (pagar, pánico, armar/desarmar) → confirmación explícita + reglas del pilar; nunca autónomo en lo riesgoso.
- **Privacidad** (la IA ve mucho del cliente) → control de acceso y propósito.
- **Responsabilidad** de un "asesor" (financiero/seguridad) → tono prudente, sin promesas, con escalamiento.
- **Sobre-automatización** que frustre → siempre salida a humano.

## 8. MVP — "Asesor que entiende y explica" (read-only + escala)
Asistente conversacional **fundamentado en los datos reales** del cliente que responde: "¿cuánto
debo y por qué?", "¿estoy protegido?", "¿qué pasó?", "¿por qué se suspendió mi servicio?", "¿cuándo
es mi próximo cargo?" — usando memoria de eventos + estado en vivo. **Sin acciones de riesgo**;
**handoff a humano** cuando hace falta. (Reutiliza la base de bots existentes, aterrizada en datos.)

## 9. Evolución
- **V2 — "Asesor que actúa":** ejecuta acciones con confirmación (pagar, solicitar patrulla/
  mantenimiento, agendar, actualizar método de pago) + **proactivo** (resúmenes, recomendaciones,
  alertas inteligentes) + voz.
- **V3 — "Asesor predictivo":** anticipa (riesgo de morosidad, anomalías de seguridad, próximos
  gastos), personaliza upsell/retención, mayor autonomía dentro de barreras, copiloto omnicanal.

## 10. KPIs
% de consultas resueltas sin humano (deflexión) · acciones completadas vía IA · satisfacción/CSAT de
la conversación · tasa de escalamiento y de error/corrección · impacto en cobranza (pagos iniciados
por IA) y en soporte (solicitudes abiertas/resueltas) · adopción/recurrencia del asistente.

## 11. Línea Base Operativa (PENDIENTE — datos reales post-Go-Live)
| Métrica base | Valor (pendiente) |
|---|---|
| Volumen actual de dudas/trámites por WhatsApp/teléfono | _por capturar_ |
| % potencialmente automatizable | _por capturar_ |
| Tiempo promedio de atención humana hoy | _por capturar_ |

## 12. Las 6 preguntas obligatorias
1. **Problema del cliente:** la información existe pero falta quien la interprete y actúe por él (§1).
2. **Valor Sentinela:** deflexión operativa, cobranza/autogestión más rápidas, personalización, capitaliza la memoria (§3).
3. **Indicadores:** deflexión, acciones vía IA, CSAT, escalamiento, impacto en cobranza/soporte (§10).
4. **MVP:** asesor conversacional grounded read-only + handoff (§8).
5. **Evolución 24m:** V2 actúa + proactivo; V3 predictivo/omnicanal (§9).
6. **Integración con la Plataforma de Eventos:** es su **principal consumidor** (memoria histórica) y produce eventos de interacción/acción (§6).

---
**Estado:** **artefacto oficial** (mapa de producto cerrado). SentiBot = **interfaz inteligente
omnipresente pero discreta** (copiloto), no un módulo del menú (ver PROD_00). Criterio: existe para
**reducir fricción**. Definiciones de DETALLE que se resuelven en la fase de diseño/arquitectura:
(a) acciones autónomas vs con confirmación vs solo humano; (b) canales del MVP (Portal/WhatsApp);
(c) alcance del "asesor" para acotar responsabilidad; (d) consolidación de bots actuales
(OpenClaw/SentiAI/Chatwoot) en uno.
