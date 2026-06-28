# Filosofía de Evolución de la Plataforma — Alea / Sentinela

> Cómo evoluciona el **ecosistema** (no una app). Define el **ciclo de vida de una capacidad** y los
> criterios para promoverla. Subordinado a `ALEA_PLATFORM_MASTER_PLAN.md` (la brújula). Documento corto.

## 0. Regla de oro
> **Una capacidad NO nace para reutilizarse. Se reutiliza cuando demuestra valor.**

No construimos capacidades "por si algún día sirven". El orden es siempre:
**resolver un problema real → demostrar que OTRA app necesita exactamente lo mismo → recién entonces
promover a Core.** Nunca al revés. Esto nos protege de construir una plataforma demasiado grande
demasiado pronto (anti "monolito de capacidades").

## 1. Ciclo de vida de una capacidad
```
Idea → Experimental → Consumida por 1 app → Consumida por varias → Capacidad Core → Activo Estratégico
```
| Etapa | Dónde vive | Qué la hace avanzar |
|---|---|---|
| **Idea** | Documento (pasa las 3 preguntas de gobernanza) | Hay un problema de negocio real. |
| **Experimental** | **DENTRO de una app** (acoplada está bien aquí) | Resuelve el problema para esa app. |
| **Consumida por 1 app** | En esa app, en producción | Funciona y se mide; sigue sin ser compartida. |
| **Consumida por varias** | Se **extrae** con un contrato (puerto) | **Una 2ª app necesita LA MISMA lógica** → señal de promoción. |
| **Capacidad Core** | Core (Master Plan) | Contrato estable + versionado + adaptadores; sin lógica de app. |
| **Activo Estratégico** | Core, protegido como IP | Encarna experiencia/datos/inteligencia/modelo y da ventaja competitiva. |

## 2. ¿Cuándo deja de vivir en una app y pasa a compartida?
Debe cumplir **todo** (no basta uno):
1. Una **2ª app** necesita la **MISMA** lógica (la misma, no parecida).
2. Es lógica de **dominio/negocio**, no de presentación/UX.
3. Tiene un **contrato claro y estable** posible.
4. **Extraerla cuesta menos** que mantenerla duplicada.
Si no se cumple → se queda en la app (o se comparte solo el **dato** vía una API existente).

## 3. ¿Qué pertenece al Core?
**Sí:** lo agnóstico de app/negocio, con contrato + versionado + adaptadores, fuente de verdad de
algo o puerto a proveedores. **No:** lógica de una sola app, UX, u orquestación de experiencia (eso
vive en las apps). *Capacidades hablan con capacidades; apps solo orquestan.*

## 4. ¿Cómo evitamos el "monolito de capacidades"?
- **Promoción por demanda real** (regla de oro), nunca por especulación.
- **Extender antes que crear** (las 3 preguntas): preferir ampliar una capacidad existente.
- Cada capacidad = **responsabilidad única + contrato independiente**; comunicación por contrato, no por acoplamiento de código.
- Una capacidad **sin ≥2 consumidores reales** no debería seguir en Core → revisar/degradar.
- Tamaño correcto: **tan pocas capacidades como sea posible, tan independientes como sea necesario.**

## 5. ¿Cuándo está lista para reutilizarse? (checklist "2º consumidor")
- ✅ **Contrato público** estable y documentado (no el ORM ni la implementación).
- ✅ **Adaptadores aislados** (proveedor reemplazable).
- ✅ **Sin dependencia** de la app original (no conoce su UI ni su dominio).
- ✅ **Observabilidad/medición** (sabemos si funciona).
- ✅ **Versionado + compatibilidad** (no rompe consumidores).
- ✅ **Validada por ≥1 consumidor real** en STAGING/producción.

## 6. ¿Qué significa "madura"? (niveles, alinean con Master Plan §5)
| Madurez | Señal |
|---|---|
| **Experimental** | en 1 app, sin contrato público |
| **Estable** | contrato público + 1 consumidor real |
| **Reutilizable / Core** | ≥2 consumidores + contrato versionado + adaptadores |
| **LTS / Activo estratégico** | congelada, evoluciona por compatibilidad, protegida como IP |

## 7. Foto actual (alineada con el Master Plan)
- **Ya demostraron transversalidad → Core:** Catalog Engine (LTS), Membership Engine, **Eventos** (transversal; entra a contrato Core), y le siguen **Estado** y **Notificaciones** (V1 de plataforma).
- **Todo lo demás nace en su app** y solo se promueve cuando una 2ª app necesite lo mismo.

---
**Estado:** artefacto oficial de evolución de plataforma. Cierra la filosofía. Las próximas capacidades
(las que aún no imaginamos) se rigen por este ciclo. Siguiente: contrato detallado de **Eventos**
(capacidad ya transversal → lista para promoverse a Core).
