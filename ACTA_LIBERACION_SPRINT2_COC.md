# Acta de Liberación — Sprint 2 (Vertical Cobranza) · `coc-v1.2.0`

> **PLANTILLA** — se completa DURANTE/DESPUÉS de la ventana de despliegue autorizada. Hasta entonces, permanece sin firmar.

## 1. Identificación
- **Release:** `coc-v1.2.0` (sobre RC4 `d4427b6`).
- **Fecha/hora de la ventana:** __________
- **Responsable de despliegue:** __________ · **Guardia:** __________
- **Autorización de liberación (Enrique):** __________

## 2. Decisión Stripe (§0 del plan)
- [ ] Test-primero (piloto) — hasta corte a live el __________
- [ ] Live directo
- Webhook registrado en: `https://api.sentinela.mx/v1/payments/webhook` · `whsec` cargado: [ ]

## 3. Componentes promovidos (digests reales al desplegar)
| Componente | Versión | Imagen / módulo | Digest / estado |
|---|---|---|---|
| `sentinela_api` | 18.0.0.3.1 | módulo en V18 | __________ |
| Gateway | 0.4.2 | `coc-gw:0.4.2` | `sha256:__________` |
| SPA | 0.6.0 | `coc-web:0.6.0` | `sha256:__________` |

## 4. Respaldos / rollback preparados
- Dump pre-deploy V18: `__________` (sha256 `__________`, `pg_restore --list` OK: [ ])
- Imágenes de rollback: `coc-gw:rollback-prod-sprint1` [ ] · `coc-web:rollback-prod-sprint1` [ ]
- tar `sentinela_api` 18.0.0.2.0: `__________`

## 5. Resultado del smoke end-to-end
- Pago desde `portal.sentinela.mx`: [ ] confirmado · id pago `__________` · factura `__________` → `paid` [ ]
- Reactivación (si aplica): sub `__________` → active [ ]
- Idempotencia (reenvío webhook sin doble aplicación): [ ]
- No-regresión Sprint 1: [ ]

## 6. Incidencias durante el despliegue
| # | Descripción | Severidad | Resolución / rollback |
|---|---|---|---|
| | | | |

## 7. Estado final
- [ ] **LIBERADO** — Sprint 2 en Producción, smoke en verde, sin incidencias abiertas.
- [ ] **REVERTIDO** — motivo: __________

## 8. Cierre
- Tag `coc-v1.2.0` pusheado: [ ]
- `RELEASE_NOTES_SPRINT2_COC.md` publicadas: [ ]
- Limpieza STAGING ejecutada: [ ]
- Backlog Sprint 3 abierto: [ ]

**Firma de cierre (Enrique):** __________
