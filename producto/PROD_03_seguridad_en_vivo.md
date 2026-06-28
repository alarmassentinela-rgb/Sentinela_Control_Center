# Producto — Pilar Seguridad en Vivo (el diferenciador de Alarmas Sentinela)

> Documento de PRODUCTO (qué y por qué). Orden: Producto → Procesos → Arquitectura funcional → Tecnología.
> Empezamos por la EMOCIÓN, no por la tecnología. Aplica la regla de las **6 preguntas obligatorias** (§15).

## 0. La pregunta de partida y los objetivos estratégicos
> **¿Qué tranquilidad espera sentir un cliente cuando abre el Portal?**

Que **todo está bajo control — su familia, casa, negocio y vehículos están protegidos AHORA — y que
si algo ocurre, Sentinela ya está actuando.** El Portal responde al instante: **¿Estoy protegido
ahora? · ¿Pasó algo? · ¿Quién atiende? · ¿Qué puedo hacer?**

**Dos objetivos estratégicos del pilar:**
1. **Hacer visible la tranquilidad** (estado de seguridad real y en vivo).
2. **Demostrar valor permanente:** el cliente suele recordar a la empresa **solo cuando hay un
   problema**. El Portal debe probar que **Sentinela está trabajando incluso cuando aparentemente no
   pasa nada** (pruebas, supervisión, disponibilidad, patrullajes, eventos evitados). **La confianza
   reduce cancelaciones** — este es un objetivo de negocio explícito del pilar.

## 1. Problema que resuelve (cliente)
La seguridad es **invisible**: el cliente no ve en tiempo real si está protegido, qué pasó, ni quién
atiende; y **cuando "no pasa nada" no percibe el valor** de lo que paga → la relación se vuelve
puro costo a los ojos del cliente y sube el riesgo de cancelación.

## 2. Valor para el cliente
Certeza permanente (ver que está protegido), enterarse al instante, saber que hay atención en curso,
pedir ayuda con un toque, ubicar a los suyos, y **percibir el trabajo continuo** de Sentinela aunque
no haya incidentes. Tranquilidad **visible y tangible**.

## 3. Valor para Alarmas Sentinela
Diferenciador competitivo difícil de copiar · **retención / menos cancelaciones** (confianza
permanente) · menos llamadas · upsell (alarma+GPS+internet visibles juntos) · transparencia ante
eventos (menos disputas).

## 4. Alcance del pilar (por la tranquilidad que entrega)
**"Estoy protegido ahora" (estado en vivo, compuesto §5):** estado por servicio · armado/desarmado ·
internet · salud de dispositivos · GPS en línea.
**"Sé qué pasó" (historial):** último evento · línea de tiempo de seguridad · historial de
intervenciones · evidencias.
**"Alguien está actuando":** patrulla en camino · confirmación de atención · **protocolo de pánico (§6)**.
**"Puedo actuar":** botón de pánico · solicitud de patrulla · pruebas del sistema · (V3) armar/desarmar.
**"Ubico lo mío":** GPS en tiempo real.
**"Sentinela trabaja aunque no pase nada" (valor percibido permanente):** última prueba de
comunicación · última supervisión · **tiempo protegido** · disponibilidad del servicio · estado de
dispositivos · tiempo de respuesta histórico · estadísticas de atención · patrullajes realizados ·
eventos evitados · salud general del sistema.

## 5. Estado de protección (compuesto, no una sola variable)
El "Estado de Tranquilidad" se **calcula con reglas de negocio** a partir de múltiples señales:
estado del panel · comunicación · internet · alimentación eléctrica · batería · eventos abiertos ·
patrulla en proceso · estado del servicio · salud de dispositivos.
> El usuario **siempre ve un único estado simple** (p. ej. Protegido / Atención / Alerta). Internamente
> la regla puede volverse **mucho más inteligente con el tiempo SIN cambiar la interfaz** (motor de
> estado evolutivo). Siempre con "última actualización" y degradación honesta si falta señal.

## 6. Protocolo de Pánico (V2) — no es un botón, es un proceso
Flujo completo, **todo registrado como eventos** en la Plataforma:
**Cliente → Botón de Pánico → Evento crítico → Central de Monitoreo → Operador → Patrulla/Autoridad →
Seguimiento → Cierre → Evidencias → Timeline.**
El cliente puede **ver la trazabilidad**: cuándo se recibió · quién lo tomó · cuándo se despachó ·
quién atendió · cuándo terminó. (No "se envió un botón", sino el **proceso completo de atención**.)
Requiere verificación para evitar falsos disparos.

## 7. Flujos
### 7.1 Usuario
Abre el Portal → ve **"Protegido ahora"** (§5) → si hubo algo, ve **último evento + línea de tiempo**
→ si hay evento activo, ve **patrulla en camino + confirmación** → puede **actuar** (pánico §6,
solicitar patrulla, probar sistema, GPS en vivo) → y percibe el **valor permanente** (§4) aunque no
haya incidentes.
### 7.2 Operativo / interno
Monitoreo / SentiCar / Netwatch / FSM **publican eventos** (estado, alarma, pánico, despacho,
atención, GPS/internet offline, salud, **pruebas y supervisiones**). El Portal lee **estado en vivo**
de los sistemas y **la historia** de la Plataforma de Eventos. Acciones del cliente generan eventos
que entran al flujo operativo real.

## 8. Arquitectura funcional (sin tecnología)
| Fuente | Qué entrega | Origen |
|---|---|---|
| **Estado en vivo (snapshot)** | armado/online/salud/posición | Monitoreo / SentiCar / Netwatch |
| **Historial (memoria)** | eventos, timeline, intervenciones, **pruebas/supervisiones** | **Plataforma de Eventos** (PROD_02) |

| Bloque funcional | Responsabilidad |
|---|---|
| **Motor de estado de protección** | Calcula el estado simple (Protegido/Atención/Alerta) con reglas compuestas (§5); evolutivo sin cambiar UI. |
| **Línea de tiempo de seguridad** | Vista filtrada del Timeline (consume PROD_02). |
| **Protocolo de atención/pánico** | Orquesta y muestra la trazabilidad del proceso (§6). |
| **Acciones del cliente** | Pánico / patrulla / prueba / (V3) armar-desarmar → **generan evento** + disparan operación. |
| **Ubicación (GPS en vivo)** | Posición en tiempo real (SentiCar). |
| **Valor percibido permanente** | Indicadores de trabajo continuo (§4) — muchos derivados de eventos de prueba/supervisión. |
| **Información vs Evidencia** | Dos clases de dato con reglas distintas (§9). |

### Armar / Desarmar remoto — V3 (contemplado desde ahora, NO se construye aún)
Función de **alto riesgo**; la arquitectura debe **no limitarla**, pero se difiere. Requisitos
obligatorios cuando se haga: **autenticación reforzada · autorización por cliente · compatibilidad
del panel · auditoría completa · registro de eventos · confirmación explícita.**

## 9. Información vs Evidencia (privacidad y retención)
Dos conceptos separados, con reglas propias:
- **Información:** eventos, fechas, estados, responsables. (Lo que normalmente ve el cliente.)
- **Evidencia:** fotografías, video, audio, documentos, bitácoras, GPS, reportes.
> **No todo se muestra automáticamente al cliente.** Cada tipo de evidencia tiene **privacidad y
> retención propias**; la política depende del **tipo de servicio, el contrato y la naturaleza del
> evento**. La arquitectura debe tratar la evidencia como dato gobernado (acceso/retención), no como
> un adjunto libre.

## 10. Riesgos (críticos por ser seguridad)
Falsa tranquilidad por dato en vivo desactualizado → "última actualización" + degradación honesta ·
falsos disparos/abuso del pánico → verificación + protocolo · armar/desarmar remoto (alto riesgo
legal) → requisitos §8 · **privacidad de evidencias** (§9) · responsabilidad legal de lo que se
afirma ("protegido"/"atendido") · disponibilidad de los sistemas en vivo.

## 11. MVP — "Ver que estoy protegido + sentir el trabajo continuo"
Solo lectura, sin acciones de riesgo:
- **Estado de protección compuesto** (§5) por servicio, con "última actualización".
- **Último evento + línea de tiempo de seguridad** (consume Plataforma de Eventos).
- **Notificación** de evento crítico de alarma (vía Plataforma).
- **GPS en línea / última posición**.
- **Primeros indicadores de valor permanente** (§4): tiempo protegido, última prueba/supervisión, disponibilidad.
- Degradación honesta si no hay señal.

## 12. Evolución
- **V2 — "Si algo pasa, lo veo y puedo pedir ayuda":** **protocolo de pánico completo (§6)** +
  patrulla en camino + confirmación + solicitud de patrulla + **GPS en tiempo real** + evidencias +
  historial de intervenciones + más indicadores de valor permanente (patrullajes, tiempo de respuesta, eventos evitados).
- **V3 — "Control y prevención inteligente":** pruebas del sistema remotas + **armar/desarmar (con
  requisitos §8)** + salud predictiva de dispositivos + **IA proactiva** (anomalías sobre el
  historial de eventos) + video/cámaras si hay integración + automatizaciones.

## 13. KPIs
Adopción de la vista de seguridad · **reducción de cancelaciones/churn** de clientes que usan el
pilar · reducción de llamadas ("¿está armado?/¿qué pasó?/¿ya mandaron patrulla?") · uso y tasa de
falsos del pánico/solicitudes · confirmaciones de atención vistas · **engagement con indicadores de
valor permanente** · upsell GPS/alarma desde la vista.

## 14. Línea Base Operativa (PENDIENTE — datos reales post-Go-Live)
| Métrica base | Valor (pendiente) |
|---|---|
| Cancelaciones/mes y motivo | _por capturar_ |
| Llamadas/mes "¿está armado?/¿qué pasó?/¿ya mandaron patrulla?" | _por capturar_ |
| Eventos de alarma/mes, % con intervención, tiempo de despacho | _por capturar_ |
| Pruebas/supervisiones por servicio (para "valor permanente") | _por capturar_ |

## 15. Las 6 preguntas obligatorias (resumen)
1. **Problema del cliente:** su seguridad es invisible y no percibe el valor cuando "no pasa nada" (§1).
2. **Valor para Sentinela:** diferenciador, **retención/menos cancelaciones**, menos llamadas, upsell (§3).
3. **Indicadores:** adopción, churn, llamadas evitadas, uso/falsos de acciones, engagement con valor permanente (§13).
4. **MVP:** estado compuesto + último evento + timeline + GPS en línea + notificación crítica + primeros indicadores de valor permanente (§11).
5. **Evolución 24m:** V2 protocolo de pánico/atención/GPS vivo; V3 armar-desarmar + IA proactiva (§12).
6. **Integración con la Plataforma de Eventos:** mayor productor/consumidor; el protocolo de pánico, la atención, las pruebas/supervisiones y la línea de tiempo viven como eventos (§6/§8).

---
**Estado:** definiciones cerradas (pánico-protocolo §6, armar/desarmar V3 §8, estado compuesto §5,
Información vs Evidencia §9, valor percibido permanente §0/§4). **Artefacto oficial del tercer pilar
estratégico.** Con Cobranza + Plataforma de Eventos + Seguridad en Vivo definidos, podemos pasar al
**diseño de arquitectura técnica del ecosistema completo** (no condicionada solo por Cobranza).
