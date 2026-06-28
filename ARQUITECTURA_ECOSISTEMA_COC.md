# Arquitectura del Ecosistema Sentinela (v1.0 — oficial)

> **Vista de CAPACIDADES, subordinada a `ALEA_PLATFORM_MASTER_PLAN.md` (la brújula y única fuente de
> verdad).** Mismo ecosistema, distinto zoom: este documento detalla las capacidades; el master plan
> ubica las capas, componentes, contratos y la clasificación estratégica. No es una arquitectura paralela.
> Arquitectura al servicio de la visión (`producto/PRODUCT_VISION.md`). Diseño, no código.
> **Primero las CAPACIDADES de negocio; la tecnología es solo un adaptador.**
> El **COC (Portal del Cliente) es el primer consumidor**, no el centro de la arquitectura.

## 0. Principios arquitectónicos fundamentales (innegociables)
1. **Plataforma de capacidades, no app-céntrica.** Diseñamos la plataforma del ecosistema Sentinela;
   las aplicaciones (Portal, móvil, distribuidores, monitoreo, técnicos, patrullas, SentiBot, IA
   interna, automatizaciones, APIs de terceros) son **clientes delgados**.
2. **Las CAPACIDADES se comunican entre capacidades; las APLICACIONES solo orquestan experiencias.**
   La **lógica de negocio vive dentro de las capacidades**, nunca en las apps. Así cualquier app
   futura reutiliza exactamente la misma plataforma.
3. **Lenguaje de negocio, no implementaciones.** La arquitectura se describe por lo que cada capacidad
   **hace** ("Eventos publican", "Pagos autorizan", "Documentos generan", "Estado consulta"), nunca
   por su tecnología ("llama a Odoo/Stripe"). Cada capacidad tiene **uno o varios adaptadores** que
   implementan ese comportamiento → se puede **cambiar de tecnología sin cambiar el lenguaje de negocio**.
4. **Identidad unificada y transversal.** Un solo sistema de identidad para **todos los actores**
   (cliente, distribuidor, técnico, operador); lo único que cambia son **roles, permisos y capacidades**.
5. **Eventos = memoria del ecosistema, con Event Store propio.** Capacidad independiente; los sistemas
   (Odoo, SentiCar, Netwatch, FSM, Gateway) son **productores**, no el almacén de eventos.
6. **Comandos síncronos; consecuencias por eventos.** (Detalle en §4.)
7. **Puertos y adaptadores para proveedores** (pago, canales, GPS): el proveedor es reemplazable.

---

## 1. ¿Cuáles son las capacidades del ecosistema? (Q1)
Capacidades descritas por su **verbo de negocio** (no por tecnología). 🟢 = **V1 de la plataforma**.

| # | Capacidad | Qué HACE (lenguaje de negocio) | V1 |
|---|---|---|:--:|
| C1 | **Identidad** | **Autentica y autoriza** a cualquier actor; gestiona roles y permisos. | 🟢 |
| C2 | **Eventos** | **Publican y registran** todo lo que ocurre; son la memoria histórica. | 🟢 |
| C3 | **Estado** | **Consulta** el "ahora" (armado, online, salud, saldo, posición). | 🟢 |
| C4 | **Notificaciones** | **Entregan** avisos por el canal y criticidad correctos. | 🟢 |
| C5 | **Pagos** | **Autorizan y aplican** cobros; resguardan medios de pago. | 🟢 |
| C6 | **Documentos** | **Generan y entregan** facturas, CFDI, recibos, evidencias. | 🟢 |
| C7 | **Servicios y Contratos** | **Definen** qué tiene el cliente y su estado contractual. | — |
| C8 | **Acciones** | **Ejecutan** comandos del dominio. | — |
| C9 | **IA** | **Razona y asesora**; invoca acciones con barreras. | — |
| C10 | **Ubicación** | **Localiza** (posición en vivo, recorridos, geocercas). | — |
| C11 | **Comunicación** | **Conversa** (mensajería bidireccional). | — |
| C12 | **Agenda** | **Programa** visitas, ventanas y despacho. | — |
| C13 | **Auditoría** | **Registra** de forma inmutable quién hizo qué. | — |
| C14 | **Catálogo** | **Consulta** productos/categorías/atributos/precios/disponibilidad/equivalencias/búsqueda; **abstrae a todos los distribuidores** (el consumidor solo "Consulta Catálogo"). | ✅ existe (Catalog Engine v1.0 LTS) |

> **V1 = Identidad · Eventos · Estado · Notificaciones · Pagos · Documentos** (capacidades nuevas a
> construir). **Catálogo (C14) YA existe** (Catalog Engine v1.0 LTS) y el **Portal será su primer
> consumidor en STAGING** (caso real de validación antes de otras apps). Con esas seis + Catálogo se
> sostienen el Portal, SentiBot y gran parte del ecosistema; el resto se incorpora conforme evolucione.
> *(Servicios/Contratos se sigue consumiendo de lo existente (`sentinela_api`) hasta formalizarse como
> capacidad; no bloquea V1.)*

## 2. ¿Qué aplicaciones consumen cada capacidad? (Q2)
Ninguna capacidad pertenece a una app. (✅ = consumidor natural.)

| Capacidad | Portal | Móvil | Distrib. | Monitoreo | Técnicos | Patrullas | SentiBot | IA int. | Automatiz. | Terceros |
|---|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| Identidad | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Eventos | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Estado | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Notificaciones | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | | ✅ | ✅ |
| Pagos | ✅ | ✅ | ✅ | | | | ✅ | | ✅ | ✅ |
| Documentos | ✅ | ✅ | ✅ | | ✅ | | ✅ | ✅ | | ✅ |

> Las apps **orquestan experiencias** combinando estas capacidades; **no** implementan su lógica.

## 3. ¿Qué datos son la única fuente de verdad? (Q3)
Cada dato tiene **un solo dueño**; los demás lo **leen** vía capacidad/evento, nunca lo copian.

| Dato | Dueño / fuente única de verdad |
|---|---|
| Identidad, roles, permisos | **Identidad** |
| **Historial de "qué pasó"** | **Eventos (Event Store propio)** |
| Estado de alarma en vivo | Monitoreo (productor de eventos) |
| Estado de red/internet | Netwatch (productor) |
| Posición/recorridos GPS | Ubicación (SentiCar, productor) |
| Servicios/suscripciones/contratos | Servicios y Contratos (Odoo, productor) |
| Facturas/CFDI/documentos | Documentos (Odoo, productor) |
| Resultado del cobro / medio guardado | Pagos (procesador, vía adaptador) |
| Pago aplicado / "pagada" / contabilidad | Servicios/Finanzas (Odoo) |
| Órdenes/visitas/agenda | Agenda/FSM (Odoo) |
| Preferencias de notificación | Notificaciones |
| Registro inmutable de acciones | Auditoría (sobre Eventos) |

> **Odoo NO es el Event Store**: es un **productor** de eventos, igual que SentiCar, Netwatch, FSM y
> el propio Gateway. La memoria histórica vive en la capacidad de Eventos, independiente.

## 4. ¿Qué es síncrono y qué es dirigido por eventos? (Q4)
> **Patrón columna vertebral: comandos SÍNCRONOS, consecuencias por EVENTOS.**
- **Síncrono:** Identidad autentica · Estado consulta · Acciones ejecutan (ack) · Pagos autorizan
  (inician) · Documentos generan/entregan a demanda.
- **Eventos:** Eventos publican · Notificaciones entregan · Auditoría registra · confirmación de pago
  (resultado → evento → aplica → reactiva) · refresco de Estado · IA proactiva · Automatizaciones.
- **Verdad temporal:** del **historial** = Eventos; del **ahora** = la capacidad/sistema dueño,
  mantenido fresco por eventos.

---

## 5. Las 6 capacidades de la V1 (qué hacen + sus adaptadores)
Cada capacidad expone un **contrato** (lo que hace) y se implementa con **adaptadores** (reemplazables).

| Capacidad (verbo) | Contrato (negocio) | Adaptador(es) inicial(es) |
|---|---|---|
| **Identidad** autentica/autoriza | login, sesión, roles/permisos por actor | OTP (gateway) + partner (Odoo) |
| **Eventos** publican/registran | publicar evento, leer historial, suscribir | Event Store propio + productores (Odoo, SentiCar, Netwatch, FSM, Gateway) |
| **Estado** consulta | snapshot por servicio (compuesto) | lectores de Monitoreo/Netwatch/SentiCar/Finanzas |
| **Notificaciones** entregan | enrutar por criticidad/preferencia y entregar | correo · WhatsApp · push |
| **Pagos** autorizan/aplican | autorizar cobro, guardar medio, reembolsar | procesador de pago (1er adaptador) + aplicación contable (Odoo) |
| **Documentos** generan/entregan | emitir y entregar factura/CFDI/recibo/evidencia | facturación/CFDI (Odoo) + almacén de evidencias |

> Se lee en **lenguaje de negocio**; los nombres de proveedor son **adaptadores intercambiables**,
> nunca parte del contrato. Cambiar un proveedor = cambiar su adaptador, sin tocar la capacidad ni las apps.

## 6. Gateway único
**Un solo Gateway** para toda la plataforma: punto de entrada que **autentica, compone capacidades y
orquesta** para las apps — **sin contener lógica de negocio** (esa vive en las capacidades). Si una
app necesita optimizaciones específicas, se añaden **capas adicionales** sobre el mismo Gateway, sin
romper la arquitectura. Punto de partida: **Gateway único**.

## 7. El COC como primer consumidor (y el Sprint 1)
El COC se construye **sobre** estas capacidades (no las inventa). El Sprint 1 ya tiene el germen
(Gateway + `sentinela_api` exponiendo capacidades de Odoo + Design System). Evolución: el COC
consume Identidad/Eventos/Estado/Notificaciones/Pagos/Documentos como **cualquier otra app**;
SentiBot y el Timeline (Eventos) se suman como superficies. La app móvil y el portal de distribuidores
reusarán **las mismas seis capacidades**, no una copia.

## 8. ADRs (decisiones estructurales)
- **ADR-1 Plataforma de capacidades** (no app-céntrica). *Apps delgadas; lógica en capacidades.*
- **ADR-2 Capacidades hablan con capacidades; apps solo orquestan.** *Reúso total entre apps.*
- **ADR-3 Lenguaje de negocio + puertos/adaptadores.** *Cambiar tecnología sin cambiar el contrato.*
- **ADR-4 Identidad unificada transversal** (un actor, muchos roles).
- **ADR-5 Eventos con Event Store propio**; Odoo y demás son productores. *Memoria como activo independiente.*
- **ADR-6 Comandos síncronos, consecuencias por eventos.** *Desacople y escalabilidad.*
- **ADR-7 Gateway único** (capas adicionales solo si se justifican).

## 9. Por qué esto acompaña a Sentinela durante años
Capacidades estables descritas en lenguaje de negocio + tecnología en adaptadores reemplazables +
eventos como memoria + identidad transversal + un solo Gateway → se pueden **agregar apps**, **cambiar
proveedores** y **sumar inteligencia/automatización** sin reinventar. Cada necesidad nueva es **un
consumidor más** de capacidades existentes.

---
**Estado:** **artefacto oficial de arquitectura v1.0.** Decisiones cerradas (identidad unificada,
Event Store propio, Gateway único, V1 de 6 capacidades, lenguaje de negocio/adaptadores, capacidades
hablan con capacidades). Siguiente: **detallar el contrato de cada una de las 6 capacidades V1**
(qué expone, qué eventos publica/consume, qué adaptadores) — sigue siendo diseño, antes de código.
