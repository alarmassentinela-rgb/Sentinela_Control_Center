# Producto — Experiencia Unificada del Portal (capa que une los 5 pilares)

> Documento de PRODUCTO / EXPERIENCIA (qué y por qué). Está **por encima** de los 5 pilares: define
> cómo el cliente percibe **un solo producto**, no cinco módulos. Orden: Producto → Procesos →
> Arquitectura → Tecnología. Esta capa debe **condicionar** la arquitectura técnica (la arquitectura
> sirve a esta experiencia, no al revés).

## 0. Identidad y criterio único de diseño
> **El producto es el Centro de Operaciones del Cliente. Su identidad completa es el ESTADO DE
> TRANQUILIDAD — no un componente del dashboard, sino la razón de ser del producto.**

Por eso el **criterio único de diseño** de todo lo que construyamos es una sola pregunta:
> ### ⭐ "¿Esto AUMENTA o DISMINUYE la tranquilidad del cliente?"
- Si **aumenta** la tranquilidad → pertenece al producto.
- Si **no** → probablemente es complejidad sin valor y no debe construirse.

**Cada pilar existe por su propósito de tranquilidad, no por su función:**
- **Centro Financiero** no existe para mostrar facturas → existe para dar **tranquilidad financiera**.
- **Plataforma de Eventos / Timeline** no existe para listar eventos → existe para **demostrar que Sentinela está trabajando por él**.
- **Centro de Soporte** no existe para abrir tickets → existe para **resolver con el menor esfuerzo posible**.
- **SentiBot** no existe para conversar → existe para **reducir la fricción** entre el cliente y cualquier acción.
- **Seguridad en Vivo** es la tranquilidad hecha visible.

## 1. Principio rector de experiencia
> **Los cinco pilares existen como capacidades internas; el usuario percibe UNA sola experiencia.**

El cliente nunca piensa "voy al módulo de IA / de Soporte / de Cobranza". Simplemente **mira su
estado, pregunta, pide o paga** — y el producto resuelve por dentro usando el pilar que corresponda.
Dos piezas hacen esto posible:
- **SentiBot = la interfaz inteligente del ecosistema** (no un módulo del menú): omnipresente pero discreto (copiloto).
- **Plataforma de Eventos = el tejido conectivo** que une todo, **invisible** para el cliente.

## 1. ¿Qué ve el cliente al abrir el portal?
**Una sola pantalla que responde "¿estoy bien?":** el **Estado de Tranquilidad** (seguridad + finanzas
fusionadas en un estado simple) y, debajo, **lo importante que requiere su atención**. No un tablero
con cinco secciones, sino **la respuesta a su única pregunta real: ¿todo está en orden?**

A partir de ahí, todo fluye sin cambiar de "app":
- Si tiene una **duda** → le pregunta a **SentiBot** (no "entra al módulo de IA").
- Si necesita **ayuda** → **pide lo que necesita** (no "entra al módulo de Soporte").
- Si quiere **pagar** → lo hace **desde donde tenga sentido** (en el estado, en una factura, en una notificación, o pidiéndoselo a SentiBot).
- Si quiere saber **qué pasó** → toda la historia vive en **un solo Timeline**.

## 2. Las superficies del producto (pocas, no cinco secciones)
El portal se reduce a **un puñado de superficies**; los pilares se manifiestan a través de ellas:

| Superficie | Qué es | Pilares que la alimentan |
|---|---|---|
| **Inicio — Estado de Tranquilidad** | La respuesta instantánea "¿estoy bien?" + lo que requiere atención | Seguridad (corazón) + Cobranza (saldo/atención) + Eventos (qué requiere acción) |
| **SentiBot** | Interfaz inteligente **omnipresente** (preguntar / pedir / actuar) | Todos (orquesta) |
| **Timeline** | **Una sola** historia de todo lo que pasa | Plataforma de Eventos (memoria), filtrable |
| **Acciones contextuales** | Pagar · Solicitar · Ver ubicación · Abrir servicio: **donde tienen sentido** | Cobranza · Soporte · Seguridad |
| **Detalle bajo demanda** | Un servicio / una factura / una orden | El pilar correspondiente, abierto desde Inicio/Timeline/SentiBot |

> No hay un menú "Cobranza · Seguridad · Soporte · IA · Eventos". Hay **Inicio, Timeline y SentiBot
> siempre presentes**; el resto aparece **en contexto**.

## 3. Cómo se manifiesta cada pilar SIN ser una sección
- **Plataforma de Eventos:** **invisible**. El cliente nunca la "ve"; la vive como el **Timeline** y como las **notificaciones**. Es la infraestructura que conecta todo.
- **Seguridad en Vivo:** es el **corazón del Inicio** (Estado de Tranquilidad) + su **línea de tiempo** dentro del Timeline + **acciones** (pánico, solicitar patrulla) en contexto.
- **Cobranza:** aparece en el **Inicio** (saldo / lo que requiere atención), como **acción "Pagar"** donde tenga sentido, en el **Timeline** (pagos), y vía **SentiBot** ("paga mi factura").
- **Soporte y Operaciones:** **no es una sección**; es "**pido lo que necesito**" desde el contexto (una falla en un servicio, una visita) o desde **SentiBot**; el seguimiento vive en el **Timeline**.
- **SentiBot:** es **superficie en sí** — omnipresente, no un destino del menú. Es el atajo universal a cualquier capacidad.

## 4. Modelo de navegación
- **Mínimo:** Inicio · Timeline · (SentiBot omnipresente) · Perfil/Cuenta. Sin menú de cinco módulos.
- **Contexto sobre navegación:** se llega al detalle (factura, servicio, orden) **desde** Inicio,
  Timeline o SentiBot — no navegando una jerarquía de secciones.
- **Conversación sobre menús:** lo que sería "buscar en qué módulo está" se resuelve **preguntándole a SentiBot**.
- **Acción donde tiene sentido:** las acciones (pagar, pedir, ver) viven **junto al dato**, no en un módulo aparte.

## 5. Principios de experiencia
1. **Un solo producto** (cero sensación de cambiar de app).
2. **Una sola pregunta de entrada:** ¿estoy bien? → Estado de Tranquilidad.
3. **Una sola historia:** Timeline único.
4. **Una sola interfaz inteligente:** SentiBot omnipresente.
5. **Complejidad oculta:** los pilares y la Plataforma de Eventos existen por dentro; el cliente no los percibe.
6. **Contexto > navegación; conversación > menús; acción junto al dato.**

## 6. El flujo narrativo (cómo se siente)
Abro el portal → veo mi **Estado de Tranquilidad** y **lo que requiere mi atención** → si dudo, **le
pregunto a SentiBot** → si necesito algo, **lo pido** ahí mismo → si quiero pagar, **pago** desde
donde estoy → si quiero saber qué pasó, **abro el Timeline**. **Nunca** elegí un "módulo".

## 7. Implicaciones para la arquitectura técnica (para cuando bajemos)
Esta experiencia **exige** que la arquitectura nazca pensada así:
- **Eventos como columna vertebral** (Timeline, notificaciones, contexto de SentiBot salen de ahí).
- **SentiBot necesita acceso transversal** a todos los pilares (leer memoria/estado + ejecutar acciones con barreras) → los pilares deben exponer **capacidades reutilizables**, no pantallas.
- **Acciones como componentes reutilizables** (Pagar, Solicitar, Ver) invocables desde cualquier
  superficie (Inicio, Timeline, SentiBot, detalle) — coherente con el Design System (Sprint 1).
- **Estado de Tranquilidad compuesto** que fusiona señales de varios pilares en un estado simple (PROD_03 §5).
- Los pilares = **servicios/capacidades** detrás de pocas superficies, no aplicaciones separadas.

## 8. Qué simplifica esto (antes de la tecnología)
- Menos pantallas y menos navegación → **menos a construir y mantener**.
- Una sola historia (Timeline) en vez de "historiales" por módulo.
- Las acciones se diseñan **una vez** y se reutilizan en todas las superficies.
- SentiBot reduce la necesidad de UI para casos de baja frecuencia (lo resuelve la conversación).
- La arquitectura se diseña para **capacidades + superficies**, no para cinco apps.

## 9. Relación con el Sprint 1 (evolución, no ruptura)
El Sprint 1 ya tiene el germen: **Estado de Tranquilidad** como Inicio y un Design System unificado.
La evolución natural: **el Timeline se vuelve superficie central**, **SentiBot se vuelve omnipresente**
y la navegación por secciones (hoy Inicio/Servicios/Facturación/Soporte) **se reduce** a favor de
contexto + conversación. (No se toca el Sprint 1 ahora; es la dirección a la que evolucionamos.)

## 10. Decisiones de experiencia (cerradas)
1. **SentiBot omnipresente pero discreto desde el inicio:** un **copiloto siempre disponible**, no un chatbot invasivo.
2. **Timeline = superficie de primer nivel** (después del Estado de Tranquilidad): el lugar donde el cliente entiende qué pasó y por qué.
3. **Servicios y Facturación se mantienen varias versiones:** muchos clientes piensan en esos conceptos; la unificación se construye por dentro, pero la **transición es gradual** (no se eliminan de golpe).
4. **Equilibrio objetivo ~70% visual / 30% conversacional:** el cliente resuelve casi todo **visualmente**; SentiBot interviene para **preguntar, recibir recomendaciones o ejecutar acciones complejas**. No un producto donde haya que escribir para todo.

---
**Estado:** **artefacto oficial — keystone del mapa de producto.** Define la identidad (Centro de
Operaciones del Cliente), el criterio único de diseño (¿aumenta la tranquilidad?) y la experiencia
unificada que **condiciona** la arquitectura técnica del ecosistema.
