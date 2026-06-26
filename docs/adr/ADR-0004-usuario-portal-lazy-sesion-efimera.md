# ADR-0004 — Usuario portal lazy + sesión Odoo efímera (sin API keys)

**Estado:** Aceptada (26-jun-2026)

## Contexto
Las record rules (ADR-0003) requieren un usuario Odoo cuyo `partner_id` define el alcance. Pre-crear miles de `res.users` es pesado; y el cliente prefirió **no** usar credenciales permanentes/API keys.

## Decisión
- **Usuario portal "lazy":** se crea en el **primer login**, vinculado al `res.partner` (idempotente, robusto ante concurrencia con savepoint).
- **Sesión Odoo efímera:** el gateway, tras verificar identidad, pide a Odoo (endpoint interno con secreto) que abra una **sesión Odoo de vida corta** del usuario portal y opera con ella. **No** se emiten API keys permanentes.

## Consecuencias
- (+) Las record rules aplican nativamente (el request corre como el usuario portal).
- (+) Sin credenciales permanentes; sesión revocable y expirable.
- (−) `res.users` crece con clientes activos (sin costo de licencia en Community; monitorear).
