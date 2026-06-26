# Checklist final de aceptación — Portal COC RC1

> **Gate del go-live.** Solo con TODO en ✅ se programa la ventana única de despliegue a Producción.
> Estado global: ⏳ EN PREPARACIÓN.

## A. Funcionalidad / pruebas
- [x] Suite Gateway unit: **36/36** ✅
- [x] E2E Gateway↔Odoo (datos reales, STAGING): **8/8** ✅
- [x] Suite Odoo seguridad: **19/19** ✅
- [x] Aislamiento por cliente (6 modelos, datos reales) ✅
- [ ] **Smoke real de OTP** (instancia WhatsApp conectada) ⏳ — *gate operativo*

## B. Seguridad
- [x] PenTest probes (endpoints internos + sesión forjada + timing): **6/6** ✅
- [x] Record rules = primera línea de defensa; access revocable ✅
- [x] Sin secretos/OTP en logs ✅
- [x] Magic links un-solo-uso; refresh rotativo + reuse ✅
- [x] Hallazgo `sign.document` corregido + test de regresión ✅
- [ ] `/coc/internal/*` confirmado restringido a LAN en Producción ⏳

## C. Rendimiento
- [x] Record rules sobre volumen real: 0.006 s ✅
- [x] Gateway micro-bench dentro de objetivo ✅
- [ ] (Opcional) Prueba de carga (k6/locust) antes de abrir a miles ⏳

## D. Observabilidad
- [x] Logs estructurados + `request_id` ✅
- [x] `/metrics`, `/v1/providers/health`, `/health` ✅
- [ ] Alertas configuradas en el monitoreo (proveedor down, error-rate, reuse) ⏳

## E. Documentación
- [x] Release Notes ✅
- [x] Runbook de despliegue + Rollback ✅
- [x] Checklist de Producción ✅
- [x] Smoke / PenTest / Performance / Observabilidad ✅
- [x] Bitácora de releases (Sprint 00–03) ✅

## F. Operativo / aprobación
- [ ] Respaldos verificados justo antes de la ventana ⏳
- [ ] Secretos en vault/env (no en repo) ⏳
- [ ] **Aprobación de Enrique** del RC1 ⏳
- [ ] Ventana única de despliegue programada ⏳

> Pendientes (⏳) son del cierre operativo: smoke real OTP (tras reconectar WhatsApp), confirmación LAN, alertas, respaldos y aprobación. El desarrollo del RC está completo y validado.
