# Backlog Técnico — Módulo de Membresías (`sentinela_subscriptions`)

**Estado del módulo:** 🧊 **CONGELADO (modo mantenimiento)** desde el 28-jun-2026.
Solo se permiten: correcciones de errores reales, ajustes fiscales/regulatorios, adaptaciones a futuras versiones de Odoo, y mejoras de rendimiento **que no cambien el comportamiento funcional**.
**Este backlog NO se implementa ahora** — se administra; se evaluará cuando el resto del ERP esté estabilizado, por fases, en STAGING, reversible y con aprobación.

**Leyenda** · Prioridad: 🔴 Crítica · 🟠 Importante · 🟡 Deseable · Esfuerzo: S (≤1d) · M (2-4d) · L (1-2 sem)

---

## Seguridad
| ID | Ítem | Prioridad | Riesgo | Esfuerzo | Impacto esperado | Dependencias |
|---|---|---|---|---|---|---|
| SEC-1 | **Record rules por `partner_id`** al exponer suscripciones a Portal/API (evitar fuga de datos entre clientes) | 🟠 | Fuga de información entre clientes si el Portal crece | M | Aislamiento multi-cliente seguro | Portal COC / `sentinela_api` |
| SEC-2 | Revisión de **grupos/permisos** (acoplamiento FSM↔Suscripciones ya documentado) y de campos sensibles | 🟡 | Accesos indebidos / errores de permiso | S | Permisos consistentes | — |

## Rendimiento
| ID | Ítem | Prioridad | Riesgo | Esfuerzo | Impacto esperado | Dependencias |
|---|---|---|---|---|---|---|
| PERF-1 | **Batching + commit por grupo** en `_cron_generate_pre_invoices` (hoy 1 sola transacción) | 🔴 | Timeout/memoria al crecer; corte = se pierde todo el avance | M | Facturación estable a miles de subs | — |
| PERF-2 | **Índices** en `next_billing_date`, `state`, `partner_id`, `billing_mode` (hoy solo PK) | 🔴 | Escaneos completos a volumen alto | S | Búsquedas/cron rápidos a escala | — |

## Escalabilidad
| ID | Ítem | Prioridad | Riesgo | Esfuerzo | Impacto esperado | Dependencias |
|---|---|---|---|---|---|---|
| ESC-1 | **`company_id` / multi-empresa** (hoy single-company) | 🟡 | No soporta varias empresas legales | L | Operar múltiples razones sociales | Decisión de negocio |
| ESC-2 | Validar flujo a **cientos de facturas/día** (lote mensual concentrado) | 🟠 | Estrés el día de corte | M (depende de PERF-1) | Picos de facturación sin riesgo | PERF-1 |

## Calidad (integridad funcional)
| ID | Ítem | Prioridad | Riesgo | Esfuerzo | Impacto esperado | Dependencias |
|---|---|---|---|---|---|---|
| CAL-1 | **Clave única anti-duplicado** del billing (hoy búsqueda por texto de etiqueta de periodo) | 🔴 | **Factura duplicada** si cambia el formato de etiqueta o hay carrera | M | Idempotencia garantizada a nivel BD | — |
| CAL-2 | **Lock / `SELECT FOR UPDATE`** o guardia transaccional en generación (cron + manual) | 🟠 | Duplicado en carrera cron↔manual | M | Sin duplicados concurrentes | CAL-1 |
| CAL-3 | **Prorrateo** en alta/baja/cambio de plan a mitad de ciclo (si el negocio lo requiere) | 🟡 | Cobro impreciso en cambios | M | Facturación justa | Decisión de negocio |
| CAL-4 | **Descuentos** modelados en el recurrente | 🟡 | Descuentos manuales fuera del flujo | S-M | Promociones/CxC correctas | Decisión de negocio |

## Arquitectura
| ID | Ítem | Prioridad | Riesgo | Esfuerzo | Impacto esperado | Dependencias |
|---|---|---|---|---|---|---|
| ARQ-1 | **Modularizar** `subscription.py` (2,589 líneas; separar overrides de `account.move`/`sale.order` a archivos propios) | 🟠 | Mantenibilidad y riesgo de upgrade | L | Más fácil mantener/migrar | — |
| ARQ-2 | **Interfaz pública estable** (ver `CONTRATO_MODULOS_*`) sin acoplar internals | 🟠 | Acoplamientos entre módulos | M | Integraciones desacopladas | Contrato definido |
| ARQ-3 | Estudio de **OCA `contract`** como base de la recurrencia pura (evaluación, NO migración) | 🟡 | — | M | Decisión informada a futuro | — |

## Observabilidad
| ID | Ítem | Prioridad | Riesgo | Esfuerzo | Impacto esperado | Dependencias |
|---|---|---|---|---|---|---|
| OBS-1 | **Telemetría del cron de facturación** (nº generadas, fallos, duración, montos) — hoy solo `_logger.error` | 🟠 | Fallos silenciosos no detectados a tiempo | S-M | Detección temprana de problemas | — |
| OBS-2 | Alertas por **grupo fallido** en la generación (hoy se loguea y continúa) | 🟡 | Grupo sin facturar pasa inadvertido | S | Cero facturas "perdidas" | OBS-1 |

## Pruebas
| ID | Ítem | Prioridad | Riesgo | Esfuerzo | Impacto esperado | Dependencias |
|---|---|---|---|---|---|---|
| TEST-1 | **Suite de pruebas del flujo de facturación** (generación, agrupación, anti-duplicado, cobro adelantado, suspensión/reactivación) — hoy **sin `tests/`** | 🟠 | Regresiones invisibles en cada cambio | L | Cambios seguros; red de seguridad | — |
| TEST-2 | Fixtures de escenarios fiscales (PUE/PPD, frontera 8%/16%, remisión vs factura) | 🟡 | Errores fiscales en casos borde | M | Confianza fiscal | TEST-1 |

---

## Resumen de prioridades
- **🔴 Críticas (3):** CAL-1 (clave única anti-duplicado), PERF-1 (batching/commit), PERF-2 (índices). Todas son **quirúrgicas y sin cambio de comportamiento** → candidatas naturales cuando se autorice tocar el módulo.
- **🟠 Importantes (7):** SEC-1, ESC-2, CAL-2, ARQ-1, ARQ-2, OBS-1, TEST-1.
- **🟡 Deseables (9):** el resto.

> Regla de gobierno: ningún ítem se implementa hasta que (a) exista necesidad real, (b) el resto del ERP esté estabilizado, y (c) se haga en STAGING, reversible y aprobado. El módulo permanece **congelado** entretanto.
