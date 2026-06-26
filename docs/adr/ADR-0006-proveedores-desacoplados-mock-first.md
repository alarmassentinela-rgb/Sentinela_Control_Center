# ADR-0006 — Proveedores desacoplados + Mock-first; EvoApi 1ª impl real

**Estado:** Aceptada (26-jun-2026)

## Contexto
El envío de OTP (y el acceso a Odoo) no debe acoplar el gateway a un servicio externo concreto; y se quería validar todo el flujo sin depender de servicios externos.

## Decisión
- Interfaces desacopladas: **`OtpProvider`** (Mock/EvoApi) y **`OdooClient`** (Http/Fake).
- **Mock-first:** todo el flujo (OTP, sesiones, JWT, recuperación) se valida con Mock + SQLite antes de integrar EvoApi.
- **EvoApi** como primera implementación real, con health check, circuit breaker, reintentos, métricas y sin loguear secretos/OTP.

## Consecuencias
- (+) Cambiar de proveedor = configuración, no código.
- (+) Pruebas automatizadas completas sin servicios externos.
- (−) Mantener stubs/fakes; mitigado por su simplicidad.
