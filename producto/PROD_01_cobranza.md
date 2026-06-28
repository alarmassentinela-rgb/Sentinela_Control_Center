# Producto — Pilar Cobranza y Finanzas · Centro Financiero del Cliente

> Documento de PRODUCTO (qué y por qué). Orden: Producto → Procesos → Arquitectura funcional → Tecnología.
> **Stripe es una IMPLEMENTACIÓN del motor de pago, no la arquitectura.** El producto nunca asume
> un proveedor; el motor de pago es intercambiable (puerto + adaptador). Base: Sprint 1 ya tiene
> estado de cuenta, facturas (por pagar/vencida/pagada) y la UX de selección + resumen de pago.

## 0. Visión del pilar — Centro Financiero del Cliente
> **La Cobranza no se diseña para "recibir dinero": es el CENTRO FINANCIERO del cliente.**

Al entrar al portal, el cliente debe sentir que ahí **administra toda su relación económica con
Sentinela**: no solo paga, sino que **consulta, planea, descarga, programa, autoriza, recibe
comprobantes y CFDI, administra sus métodos de pago, consulta cargos futuros, recibe
recomendaciones y, eventualmente, interactúa con un asistente financiero basado en IA**.
Para el cliente = control y tranquilidad financiera; para Sentinela = cobro más rápido, menos
morosidad, menos operación y base para inteligencia de cobranza. La cobranza deja de ser centro de
costo para volverse **motor de retención y caja**.

## 1. Problema que resuelve
Pagar hoy es **fricción + trabajo manual**: el cliente va a OXXO/banco, **manda comprobante por
WhatsApp** y **espera** validación; Sentinela **concilia, aplica y reactiva a mano**. Resultado:
demora de cobro, morosidad por fricción, errores de aplicación, carga operativa y llamadas "ya
pagué, reactiven". Además, el cliente **no tiene una vista financiera** de su relación con Sentinela.

## 2. Valor para el cliente
Pagar en minutos 24/7, **confirmación inmediata**, comprobante/CFDI al instante, **reactivación
automática por servicio**, **domiciliación** ("olvídate de pagar"), **recordatorios útiles**,
historial y una **vista clara de sus finanzas** con Sentinela. Tranquilidad financiera, no un pago.

## 3. Valor para Alarmas Sentinela
Cobro más rápido (mejor flujo de caja), **menos morosidad**, **menos trabajo manual**
(conciliación/validación/reactivación), menos contactos de soporte, **datos de comportamiento de
pago** y el **cimiento** para pago recurrente, autofactura e IA de cobranza.

## 4. Alcance del pilar (ciclo completo)
Estado de cuenta · Facturas · Selección de una/varias · Pago en línea · Confirmación inmediata ·
Reactivación automática · Recibos · CFDI · Historial de pagos · Pago recurrente · Recordatorios
automáticos · IA de cobranza · Indicadores financieros del cliente.

## 5. Definiciones de negocio (aprobadas)
1. **MVP:** pago con **tarjeta y métodos compatibles con el motor (Stripe)**. Otros proveedores/métodos después, sin rediseñar.
2. **Comisiones:** las **absorbe Sentinela** en el MVP (eliminar fricción / acelerar adopción). Reevaluar traslado parcial según volumen.
3. **Reactivación POR SERVICIO/CONTRATO (no por cliente).** La **unidad de cobranza es el servicio/contrato.** El pago reactiva **solo los servicios cuya deuda quedó completamente liquidada**; un servicio **no depende** de las deudas de otro (p. ej. Alarma Casa, Alarma Negocio e Internet son independientes). Si en el futuro hay paquetes/servicios ligados, esa dependencia será una **regla de negocio configurable**, nunca una limitación técnica.
4. **Sin pagos parciales en MVP:** solo liquidación total de las facturas seleccionadas. Parciales después, con reglas específicas.
5. **Reembolsos/disputas:** el cliente los **solicita desde el portal**; la **autorización es manual** (proceso administrativo interno de Sentinela).
6. **Transición (adopción por métricas, sin % rígido):** OXXO/transferencia/banco **conviven** con el pago en línea **hasta que los indicadores de uso y de recuperación de cobranza demuestren que retirarlos mejora el negocio**. Decisión de negocio, basada en métricas reales.
7. **Pago recurrente (V2) — simple y predecible:** intenta cobrar el **importe total del ciclo vigente**. Si el cargo **falla**: (a) **no** intenta cobrar automáticamente facturas vencidas antiguas; (b) **genera un evento de cobranza**; (c) **notifica al cliente**; (d) **permite actualizar el método de pago**. Reglas más inteligentes, en el futuro.

## 6. Flujos
### 6.1 Usuario — pago puntual (MVP)
Ve saldo y facturas → selecciona (una/varias/todo) → resumen → forma de pago → confirma →
**confirmación + recibo/CFDI** → saldo actualizado + **reactivación automática por servicio** (cada
servicio cuya deuda quedó liquidada). Variantes: en proceso (formas diferidas), rechazado (reintentar).
### 6.2 Usuario — pago recurrente (V2)
Activa domiciliación (guarda su medio) → Sentinela cobra el **total del ciclo vigente** cada periodo
→ confirmación + CFDI. Si **falla**: evento de cobranza + aviso + opción de actualizar método (no se
cobran vencidas antiguas automáticamente). El cliente puede pausar/cambiar el medio.
### 6.3 Operativo interno
Pago **confirmado** → **aplicación automática** a las facturas → marca pagada → emite/envía recibo +
CFDI → **reactiva los servicios liquidados** → registra en cobranza. Cobranza pasa de
*capturar/conciliar* a **supervisar excepciones** (parciales, sobrepagos, reembolsos, disputas,
duplicados). Formas diferidas: referencia → al acreditarse, mismo flujo. Transición: OXXO/banco se
concilian como hoy hasta migrar adopción.

## 7. Arquitectura FUNCIONAL del ciclo de cobranza (sin tecnología)
**Unidad de cobranza = SERVICIO/CONTRATO** (el estado de cuenta, la deuda, la liquidación y la
reactivación se evalúan por servicio; el "cliente" es la suma de sus servicios). Bloques desacoplados:

| Bloque funcional | Responsabilidad |
|---|---|
| **Estado de cuenta (por servicio)** | Saldo / vencido / próximo, agregable por cliente pero **calculado por servicio**. |
| **Documentos** | Facturas/remisiones y su estado (por pagar/vencida/pagada), ligadas a su servicio. |
| **Intención de pago** | Qué documentos/servicios se van a pagar antes de cobrar. |
| **Motor de pago (PUERTO intercambiable)** | Cobra una intención → resultado (confirmado/en proceso/rechazado/reembolsado); guarda medio (recurrente). **Stripe = primer adaptador; reemplazable sin tocar el resto.** |
| **Aplicación de pagos** | Concilia el resultado → marca facturas por servicio, registra, maneja excepciones. |
| **Reactivación (por servicio)** | Regla def. #3; dependencias entre servicios = **regla configurable**. |
| **Comprobantes / CFDI** | Emite y envía recibo + factura. |
| **Recurrencia** | Medio guardado + agenda de cobro + reintentos + evento de fallo (def. #7). |
| **Recordatorios** | Avisos por estado/fecha (se apoya en el pilar Comunicación). |
| **IA de cobranza** | Prioriza, personaliza y predice morosidad (V3). |
| **Centro financiero (indicadores)** | Vista del cliente: §8. |
| **Excepciones** | Solicitud de reembolso/disputa (cliente) + aprobación manual (Sentinela). |

**Principio de desacople:** el ciclo **no conoce al proveedor**; habla con el *puerto* "Motor de
pago" en términos de negocio. Agregar/cambiar proveedor = nuevo **adaptador**, sin rediseñar el
producto ni la experiencia del usuario.

**Máquinas de estado:** Factura: Por pagar → Vencida → Pagada *(parcial: futuro)*. Pago: Iniciado →
En proceso → {Confirmado | Rechazado} → (Reembolsado). **Servicio:** Activo ↔ Suspendido (reactiva
al liquidarse su propia deuda).

## 8. Indicadores financieros del cliente (Centro Financiero)
- **MVP:** Saldo actual · Facturas por vencer · Facturas vencidas · Último pago · Próximo cargo · Historial de pagos · Estado de sus servicios.
- **V2:** Gasto mensual · Evolución de pagos · Ahorro por domiciliación · Pagos recurrentes · CFDI emitidos.
- **V3:** Score financiero · Predicción de gasto · Riesgo de suspensión · Recomendaciones de IA · Comparativos históricos.

## 9. Riesgos
Aplicación incorrecta del pago · "en proceso" vs "confirmado" en formas diferidas · **pago
duplicado** (en línea + depósito) → sobrepago · reactivación indebida · baja adopción · cargos no
reconocidos/fraude · cuadre fiscal del CFDI · **acoplamiento accidental al proveedor** (mitigado por
el puerto) · complejidad de **deuda/reactivación por servicio** (mitigada tratándola como modelo, no excepción).

## 10. Roadmap de evolución del pilar
**MVP (V1) — "Pagar y quedar al corriente, sin fricción".** Estado de cuenta + facturas + selección
+ **pago en línea (tarjeta vía motor=Stripe, liquidación total)** + confirmación + **reactivación
automática por servicio** + recibo + **CFDI** + historial + notificación + **indicadores MVP (§8)**.
Comisiones absorbidas; convive con OXXO/banco.

**V2 — "Olvídate de pagar + cobranza proactiva".** **Domiciliación** (def. #7) + **recordatorios
automáticos** + **solicitud de reembolso/disputa** desde el portal (aprobación manual) +
**indicadores V2 (§8)** + más métodos compatibles.

**V3 — "Centro financiero inteligente".** **IA de cobranza** (predicción/personalización) + **pago
parcial / planes / financiamiento** + pronto-pago/descuentos + pago por terceros + **listo para 2º
proveedor** + **indicadores V3 (§8)** + asistente financiero IA.

## 11. KPIs
% cobro vía portal · días de cobro · morosidad/cartera vencida · % reactivaciones automáticas (por
servicio) · conversión del flujo · adopción y recurrencia · % en domiciliación (V2) · horas de
conciliación/validación ahorradas · contactos "ya pagué/reactiven" evitados · satisfacción.

## 12. Línea Base Operativa (PENDIENTE — completar con datos reales post-Go-Live)
> A capturar de producción tras el Go-Live; alimentará el cálculo de ROI. **No bloquea este documento.**

| Métrica base | Valor (pendiente) |
|---|---|
| Facturas emitidas / mes | _por capturar_ |
| % morosidad / cartera vencida actual | _por capturar_ |
| Días promedio de cobro (emisión → pago) | _por capturar_ |
| Horas/semana en conciliación + validación de comprobantes | _por capturar_ |
| Suspensiones / reactivaciones manuales / mes | _por capturar_ |
| Mezcla actual de canales de pago (OXXO/banco/transferencia) | _por capturar_ |

## 13. ROI esperado
Aceleración de flujo de caja + menor morosidad + ahorro operativo + retención por domiciliación.
Cuantificación a partir de la **Línea Base Operativa (§12)** una vez con datos reales.

---
**Estado:** definiciones de negocio cerradas (§5) + visión de Centro Financiero (§0) + arquitectura
funcional desacoplada (§7) + indicadores por versión (§8) + roadmap MVP→V2→V3 (§10). **Artefacto
oficial del Pilar de Cobranza.** Siguiente: implementación con **Stripe como primer motor de pago**,
manteniendo la arquitectura abierta a otros proveedores sin modificar la experiencia del usuario.
