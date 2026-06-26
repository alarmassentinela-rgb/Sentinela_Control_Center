# ADR-0003 — Record rules de partner como 1ª línea de defensa

**Estado:** Aceptada (26-jun-2026)

## Contexto
Para miles de clientes externos, el aislamiento no puede depender solo del gateway: un bug de aplicación no debe exponer datos de otro cliente. La auditoría halló que los modelos customer-facing **no tenían record rules** (scoping ad-hoc en controllers).

## Decisión
Implementar **record rules de Odoo** (por `partner_id child_of commercial_partner`) en los modelos expuestos, atadas al grupo `group_coc_portal`. Son la **primera** línea de defensa; el gateway las **complementa**, nunca las sustituye.

## Consecuencias
- (+) Aislamiento garantizado a nivel de datos, robusto ante bugs del gateway/endpoints.
- (+) Validable con pruebas negativas (A no ve datos de B).
- (−) Requiere usuario Odoo por cliente activo (ver ADR-0004).
- Nota: la validación dinámica detectó y cerró un hueco pre-existente en `sign.document`.
