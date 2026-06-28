# Blueprint — Alea API Gateway (componente oficial de Alea Platform)

**Fecha:** 28-jun-2026 · **Estado:** diseño para validación (NO se escribe código aún) · Capa **Core** de Alea Platform.
El Gateway **deja de ser del Portal**: es el **punto único de acceso** de toda la plataforma. El Portal será solo su **primer consumidor**.

---

## 1. Rol y principios
- **Punto único de entrada** (single front door) a todos los motores/APIs de Alea.
- **NUNCA contiene lógica de negocio.** Solo concerns transversales (auth, caché, agregación, etc.). La lógica vive en los **motores** (Catalog, Membership, ERP, futuros).
- **API-First / contrato estable:** los consumidores hablan solo con el Gateway; no conocen Odoo, Syscom ni la topología interna.
- **Reutilización total:** web, móvil, IA e integraciones usan **exactamente** la misma infraestructura.

## 2. Posición en Alea Platform
```
Alea Platform · Core
├── Alea API Gateway        ← punto único de acceso (este blueprint)
├── Catalog Engine          (v1.0 LTS)
├── Membership Engine
└── (Public APIs de cada motor, detrás del Gateway)
```
> Eleva y generaliza el "Gateway BFF" que nació para el Portal COC (FastAPI, `api.sentinela.mx`).

## 3. Arquitectura
```
                         Internet
                            │  (TLS, CORS, WAF/rate-limit de borde)
                            ▼
                  ┌───────────────────────┐
   Consumidores → │   ALEA API GATEWAY     │  auth · authz · rate-limit · caché ·
   (web/app/IA/   │   (FastAPI)            │  agregación · versionado · auditoría ·
   integraciones/ │   SIN lógica de negocio│  correlation-id · observabilidad · seguridad
   dashboards/    └───────────┬───────────┘
   internas)                  │ service-to-service (red interna, credenciales de servicio)
        ┌──────────────┬──────┴───────┬─────────────────┬─────────────┐
        ▼              ▼              ▼                 ▼             ▼
  Catalog Engine  Membership     ERP API            Futuros        (Operations:
  /catalog/api/v1 Engine         (sentinela_api)    motores         Monitoring/FSM/GPS
  (catálogo)      (vía ERP API)  (cuenta cliente)   (vN)            cuando expongan API)
```

## 4. Consumidores (todos pasan por el Gateway)
Portal de Clientes · **App móvil** · **IA / agentes** · **Integraciones externas** (partners) · **Dashboards** · **Herramientas internas**.
Cada consumidor tiene una **identidad de consumidor** (credencial de servicio) + opcionalmente actúa **en nombre de un usuario final** (token del cliente).

## 5. Upstreams (motores detrás del Gateway)
| Motor | Qué expone | Acceso |
|---|---|---|
| **Catalog Engine** | catálogo: búsqueda, stock, specs, imágenes, docs, promote | `/catalog/api/v1` |
| **Membership Engine** | planes/membresías del cliente (vía ERP API) | ERP API |
| **ERP API (`sentinela_api`)** | cuenta del cliente: contratos, facturas, tickets, OS, dispositivos, eventos | ERP API |
| **Futuros motores** | analítica, IA, etc. | `/.../vN` |
Los motores quedan en **red interna**; el Gateway es lo único expuesto a Internet.

## 6. Responsabilidades (transversales — el Gateway las concentra)
1. **Autenticación** — de consumidor (API key/OAuth2 client-credentials) y de usuario final (token/JWT del Portal/ERP).
2. **Autorización** — scopes/roles por consumidor y por usuario (qué puede leer/hacer).
3. **Rate Limiting** — por consumidor y por usuario (global del borde + por ruta), con `429`+`Retry-After`.
4. **Caché** — respuestas cacheables (catálogo) con TTL **alineado a la frescura** del motor; backend reemplazable (memoria→Redis).
5. **Agregación de respuestas** — compone datos de varios motores en una respuesta BFF (p. ej. ficha de producto del Catalog + precio/contrato del ERP). **Composición, NO reglas.**
6. **Versionado** — ruta versionada del Gateway (`/api/v1`) que enruta a las versiones de cada motor; convivencia `/v2` futura.
7. **Auditoría** — registro de quién llamó qué, cuándo, resultado (para seguridad/forense).
8. **Correlation IDs** — genera/propaga `X-Request-ID` y `X-Correlation-ID` **hacia los motores** (trazabilidad end-to-end; el Catalog ya los acepta).
9. **Observabilidad** — logs estructurados, métricas (latencia/errores/tasa por ruta y por motor), trazas distribuidas; panel de salud del Gateway.
10. **Seguridad** — TLS, CORS, validación de entrada, ocultar campos internos (p. ej. **filtrar `cost` del Catalog**), normalización de errores, gestión de secretos, protección ante abuso.

> **Frontera dura:** si una "responsabilidad" implica decidir reglas de negocio (precio final, elegibilidad, descuentos, promoción), **NO es del Gateway** → va al motor correspondiente.

## 7. Identidad y seguridad (dos planos)
- **Plano consumidor (servicio):** cada app/integración tiene credenciales de servicio (API key/OAuth2) + scopes. El Gateway las valida y aplica rate-limit por consumidor.
- **Plano usuario final:** para datos de cuenta, el Gateway exige el **token del cliente** (sesión del Portal/ERP) y propaga su identidad a la ERP API (que aplica las record-rules por `partner_id`).
- **Catálogo:** no es por-usuario → el Gateway consulta el Catalog con su **credencial de servicio**; **nunca** expone datos internos (costo, IDs internos) al cliente.
- Secretos del Gateway en almacén seguro (no en el código); rotación.

## 8. Caché (minimizar llamadas, sin servir datos viejos donde importa)
- Cachea catálogo (búsquedas, fichas, imágenes) con TTL por tipo, leyendo `freshness.expires_at` del Catalog como pista.
- **Stock/precio al cotizar:** se confirma en vivo (bypass de caché) para no vender con datos vencidos.
- Datos de cuenta del cliente: caché muy corta o nula (privacidad/consistencia).
- Backend de caché **reemplazable** (igual filosofía que el motor).

## 9. Agregación (BFF) — composición, no lógica
- Ejemplo: "vista de producto en el Portal" = `Catalog.get_product(ref)` (specs/stock/imágenes) **+** `ERP.precio_cliente(ref)` (precio de venta/contrato) → una sola respuesta para la SPA/app.
- El Gateway **orquesta y compone**; **no** calcula precios, ni elegibilidad, ni reglas. Eso lo deciden los motores.

## 10. Versionado y enrutamiento
- Gateway expone `/<area>/api/v1/...` y enruta a la versión correspondiente de cada motor (Catalog `/catalog/api/v1`, ERP API, …).
- Cambios incompatibles → `/v2` del Gateway, conviviendo durante la deprecación (igual política SemVer que la plataforma).

## 11. Observabilidad y auditoría
- **Correlation/Request IDs** generados en el borde y **propagados a los motores** → trazabilidad de una petición a través de todo el stack.
- Métricas por consumidor/ruta/motor (latencia p50/p95, error rate, throughput), logs estructurados, trazas.
- Auditoría de accesos (consumidor, usuario, recurso, resultado) para seguridad.
- Panel de salud del Gateway + integración futura con el dashboard del Catalog y alertas.

## 12. Relación con las APIs propias de los motores
- Los motores **ya** traen sus transversales (el Catalog tiene auth/rate-limit/idempotencia). Con el Gateway al frente:
  - Los motores pasan a **red interna**; el Gateway concentra la auth de cara a Internet.
  - Entre Gateway↔motor se usan **credenciales de servicio** (defensa en profundidad; el motor sigue exigiendo su key).
  - **No se duplica lógica:** el rate-limit/caché del Gateway es el de **borde/plataforma**; el del motor es su salvaguarda interna.

## 13. Stack y despliegue
- **FastAPI** (reutiliza el gateway BFF existente del Portal COC, `api.sentinela.mx`; ya hay contenedor `gateway-*`).
- Despliegue por contenedores; **STAGING primero**; detrás de TLS (Cloudflare/NPM). Caché Redis opcional.

## 14. Orden de implementación
> ⚠️ **Actualizado (28-jun) por la `POLITICA_EVOLUCION_PORTAL`:** el Gateway es **roadmap, NO requisito** para terminar el Portal. **Prioridad = Portal** (incremental, sin rehacer). El Gateway se introduce **cuando aporte valor**; mientras tanto el Portal consume los contratos públicos (Catalog v1 / ERP API) directamente.

**Cuando se decida construir el Gateway** (sin frenar el Portal), por fases en STAGING:
1. **Gateway base**: esqueleto + auth de consumidor + propagación de IDs + observabilidad + caché.
2. **Gateway → Catalog v1**: proxy/compose de búsqueda y ficha (filtrando `cost`), con caché por freshness.
3. **Gateway → ERP API**: datos de cuenta con auth de usuario final.
4. **Agregación BFF** para las vistas del Portal.
5. El Portal **migra incrementalmente** a consumir el Gateway; la **App móvil** lo reutiliza.
Cada paso: STAGING, entregable + pruebas + reporte.

## 15. Decisiones (ADR)
- **Gateway = plataforma, no del Portal** (single front door reutilizable).
- **Cero lógica de negocio** en el Gateway (frontera dura).
- **Motores tras red interna**; Gateway única superficie a Internet.
- **Correlation IDs end-to-end** + observabilidad centralizada.
- **Caché y rate-limit de borde** ≠ los del motor (defensa en profundidad, sin duplicar reglas).

## 16. Lo que el Gateway NO es
No es un motor, no guarda la verdad del negocio, no calcula reglas/precios, no reemplaza a los motores ni a la ERP API: **orquesta y protege**, no decide.

---

## Entregable
Este **Blueprint del Alea API Gateway** (sin código). Próximo paso (tras tu visto bueno): plan de implementación por fases (§14) en STAGING, con la disciplina de entregables + pruebas + reporte. El Portal se construirá **después**, consumiendo únicamente el Gateway.
