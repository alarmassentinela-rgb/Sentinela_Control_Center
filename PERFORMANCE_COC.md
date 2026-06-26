# Validación de rendimiento — Portal COC RC1

> Mediciones en STAGING (2026-06-26). Entornos: Odoo `Sentinela_STAGING`; Gateway in-process (SQLite, 1 hilo) — cota inferior conservadora vs Postgres + workers en prod.

## 1. Aislamiento (record rules, Odoo)
- Búsqueda de un cliente portal sobre **volumen real (242 subs)**: **0.006 s**.
- Smoke de rendimiento (200 docs / 20 clientes): bajo cota de 5 s (holgado).
- **Conclusión:** las record rules no degradan las consultas del portal.

## 2. Gateway (micro-benchmark, mocks)
| Operación | n | Promedio |
|---|---|---|
| Login completo (otp/request + otp/verify + sesión + JWT + refresh) | 100 | **28.4 ms** |
| `GET /v1/sessions` (auth + query) | 100 | **13.2 ms** |
| `GET /health` | 500 | **2.3 ms** |

Notas: con FakeOdoo (sin red). En prod, el login añade la latencia del handshake Odoo (sesión efímera) y, si es login por contraseña, el costo de Argon2 (~decenas de ms, esperado y aceptable). Gateway es **stateless** → escala horizontal.

## 3. Objetivos y veredicto
| Métrica | Objetivo | Medido | Veredicto |
|---|---|---|---|
| Lectura portal (Odoo, record rule) | < 1 s | 0.006 s | ✅ |
| Login (gateway, sin red) | < 100 ms | 28 ms | ✅ |
| Endpoints autenticados | < 100 ms | 13 ms | ✅ |
| Health | < 50 ms | 2.3 ms | ✅ |

## 4. Recomendaciones
- Verificar índice en `partner_id` de los modelos expuestos (subs/eventos/dispositivos/órdenes/facturas) — `EXPLAIN` en prod.
- Caché (Redis) en el gateway para catálogos y artefactos pesados (PDF/XML) cuando lleguen los recursos de negocio.
- Re-medir bajo carga (k6/locust) antes de abrir a miles; el micro-bench es una cota, no una prueba de carga.
