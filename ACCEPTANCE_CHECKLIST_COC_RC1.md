# Checklist final de aceptación — Portal COC RC1

> **Gate del go-live.** Solo con TODO en ✅ se programa la ventana única de despliegue a Producción.
> Estado global: ✅ **RC1 DESPLEGADO EN PRODUCCIÓN (27-jun-2026).** Componente A + B en prod, smoke post-deploy verde, hardening LAN aplicado, observabilidad/alertas activas, tag `coc-v1.0.0`. Único pendiente menor: ingreso público `api.sentinela.mx` (con la SPA, Sprint 1) + token Telegram para alertas.

## A. Funcionalidad / pruebas
- [x] Suite Gateway unit: **36/36** ✅
- [x] E2E Gateway↔Odoo (datos reales, STAGING): **8/8** ✅
- [x] Suite Odoo seguridad: **19/19** ✅
- [x] Aislamiento por cliente (6 modelos, datos reales) ✅
- [x] **Smoke real de OTP** ✅ (27-jun: EvoApi `SentinelaWA` open; envío 0.56 s; verify→login OK; `/v1/me` partner correcto; record rules OK; auditoría/métricas/logs OK)

## B. Seguridad
- [x] PenTest probes (endpoints internos + sesión forjada + timing): **6/6** ✅
- [x] Record rules = primera línea de defensa; access revocable ✅
- [x] Sin secretos/OTP en logs ✅
- [x] Magic links un-solo-uso; refresh rotativo + reuse ✅
- [x] Hallazgo `sign.document` corregido + test de regresión ✅
- [x] **Restricción LAN** de `/coc/internal/*`: allowlist CIDR implementado y **validado** (enforcement OK) ✅; en Producción se fija `coc_internal_allowed_cidrs` a la red del Gateway ⏳
- [x] Robustez: `session_id` malformado → `not_found` (sin 500) ✅

## C. Rendimiento
- [x] Record rules sobre volumen real: 0.006 s ✅
- [x] Gateway micro-bench dentro de objetivo ✅
- [ ] (Opcional) Prueba de carga (k6/locust) antes de abrir a miles ⏳

## D. Observabilidad
- [x] Logs estructurados + `request_id` ✅
- [x] `/metrics`, `/v1/providers/health`, `/health` ✅
- [x] **Alert checker → Telegram** entregado (`sentinela_coc/infra/alerts/`) ✅; programar en cron de Producción ⏳

## E. Documentación
- [x] Release Notes ✅
- [x] Runbook de despliegue + Rollback ✅
- [x] Checklist de Producción ✅
- [x] Smoke / PenTest / Performance / Observabilidad ✅
- [x] Bitácora de releases (Sprint 00–03) ✅

## F. Operativo / aprobación
- [ ] Respaldos verificados justo antes de la ventana ⏳
- [ ] Secretos en vault/env (no en repo) ⏳
- [x] **RC1 aprobado técnicamente** (validación completa en verde) ✅
- [ ] **Autorización de ventana** por Enrique ⏳ (negocio)
- [ ] Ventana única de despliegue programada ⏳

## VEREDICTO
✅ **RC1 APROBADO PARA PRODUCCIÓN.** Validación técnica completa (suites + e2e + pentest + rendimiento + **smoke real de OTP de extremo a extremo**). Los ítems ⏳ restantes se ejecutan **durante la ventana** (respaldo manual, fijar CIDR LAN en prod, cron de alertas, smoke post-deploy) o son aprobación de negocio. **No se despliega hasta autorización explícita de Enrique.**
