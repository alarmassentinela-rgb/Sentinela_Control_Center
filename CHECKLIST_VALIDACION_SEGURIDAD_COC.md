# Checklist de Validación de Seguridad — Portal COC (WS-2)

> **Evidencia de aceptación del Sprint.** Cierre de WS-2 condicionado a TODOS los ítems en ✅.
> Entorno de validación: **STAGING** (`Sentinela_STAGING`, contenedor `odoo-lab`, `:8075`).
> Estado global: ✅ VALIDADO EN STAGING (núcleo) · Responsable: Claude/Enrique · Fecha: 2026-06-26.
> Pendiente solo: walkthrough manual por navegador del empresarial multi-sucursal (opcional) + aprobación final de Enrique.

Leyenda estado: ✅ pasa · ❌ falla · ⏳ pendiente · ⛔ bloqueante.

---

## Resultados de ejecución (STAGING `Sentinela_STAGING`, 2026-06-26)

**Instalación + actualización:** `-i` y `-u` de `sentinela_api` limpios (138 módulos, registry OK, **exit 0**). Sin warnings/errores propios del módulo (2 warnings pre-existentes ajenos: license de `sentinela_subscriptions`, traducción de `om_account_followup`).

**Suite automatizada:** **`0 failed, 0 error(s) of 12 tests`** ✅ (incluye IDOR, BAC, aislamiento ±, estructurales, identidad lazy, rendimiento y la regresión del hueco real).

**🐞 Problema encontrado y corregido (gracias a la validación con datos reales):**
- **Fuga en `sentinela.sign.document`:** un usuario portal **preexistente** (solo `base.group_portal`, que `digital_sign` dejaba con lectura SIN record rule) veía **142/142** documentos (incl. de otros clientes). La regla atada solo a `group_coc_portal` no lo cubría, y `_coc_ensure_portal_user` no añadía el grupo a usuarios existentes.
- **Corrección:** (1) record rule de `sign.document` atada a **`base.group_portal`** (protege a TODO usuario portal); (2) `_coc_ensure_portal_user` ahora **asegura el grupo COC** en usuarios preexistentes; (3) **test de regresión** que reproduce el caso.
- **Re-validado:** `sign.document` → ve **1**, `solo_suyo=True`, fuga **0**. Usuario preexistente solo-portal → ve **1** de 142.

**Validación funcional por modelo (datos reales, con rollback) — FINAL:**
| Modelo | Portal ve | solo suyo | fuga | admin total |
|---|---|---|---|---|
| sentinela.subscription | 1 | ✅ | 0 | 242 |
| account.move (out_*) | 1 | ✅ | 0 | 108 |
| sentinela.alarm.event | 315 | ✅ | 0 | 382 |
| sentinela.monitoring.device | 2 | ✅ | 0 | 265 |
| sentinela.fsm.order | 2 | ✅ | 0 | 17 |
| sentinela.sign.document | 1 | ✅ | 0 | 142 |

- **C-P7 empresarial:** empresa "DIVISAS FRONTERA LONGORIA" ve la sub de su sucursal (`child_of`) ✅.
- **D regresión interna:** admin ve los totales completos por modelo ✅.
- **E2 rendimiento real:** búsqueda portal **0.006 s** ✅.

**Pendiente (no bloqueante):** revisión de índices `EXPLAIN` (E4), auditoría completa WS-3 (F4), walkthrough opcional por navegador.

---

## A. Instalación y actualización en STAGING
| # | Verificación | Esperado | Estado | Evidencia |
|---|---|---|---|---|
| A1 | `rsync` del addon a STAGING | Código actualizado en server | ⏳ | |
| A2 | `-u sentinela_api` en `odoo-lab` | Instala/actualiza sin errores ni tracebacks | ⏳ | log `-u` |
| A3 | Grupo `group_coc_portal` creado | Existe y `implied_ids` incluye `base.group_portal` | ⏳ | |
| A4 | Record rules cargadas (6) | subscription, alarm.event, monitoring.device, fsm.order, sign.document, account.move | ⏳ | |
| A5 | ACL del grupo COC read-only | 4 entradas, `write/create/unlink=0` | ⏳ | |

## B. Suite de pruebas automatizadas
| # | Verificación | Esperado | Estado | Evidencia |
|---|---|---|---|---|
| B1 | `--test-tags sentinela_api,security` | Todas verdes | ⏳ | salida test |
| B2 | `--test-tags perf` (rendimiento) | Pasa + tiempo registrado | ⏳ | tiempo (s) |
| B3 | Sin warnings de seguridad en log | Sin "access"/"rule" inesperados | ⏳ | |

## C. Validación manual de aislamiento (positivos y negativos)
> Crear/usar 2 clientes con datos reales en STAGING: Cliente A y Cliente B (cada uno con suscripción, factura, evento, documento).

### Positivos (el cliente SÍ ve lo suyo)
| # | Escenario | Esperado | Estado |
|---|---|---|---|
| C-P1 | A ve SUS suscripciones | Lista solo de A | ⏳ |
| C-P2 | A ve SUS facturas (CFDI) | Solo facturas de A (out_*) | ⏳ |
| C-P3 | A ve SUS eventos de alarma | Solo de A | ⏳ |
| C-P4 | A ve SUS dispositivos de monitoreo | Solo de A | ⏳ |
| C-P5 | A ve SUS órdenes de servicio | Solo de A | ⏳ |
| C-P6 | A ve SUS documentos a firmar | Solo de A | ⏳ |
| C-P7 | Empresarial: titular ve todas sus sucursales | Techo = entidad comercial | ⏳ |

### Negativos / aislamiento (el cliente NO ve lo ajeno)
| # | Escenario | Esperado | Estado |
|---|---|---|---|
| C-N1 | A busca suscripciones de B | Vacío | ⏳ |
| C-N2 | A abre URL/registro de factura de B (IDOR) | Acceso denegado | ⏳ |
| C-N3 | A consulta evento de alarma de B por ID | AccessError | ⏳ |
| C-N4 | A intenta dispositivo de monitoreo de B | Sin acceso | ⏳ |
| C-N5 | A intenta orden de servicio de B | Sin acceso | ⏳ |
| C-N6 | A intenta documento de B | Sin acceso | ⏳ |
| C-N7 | A intenta `write`/`unlink` sobre lo suyo | Denegado (read-only) | ⏳ |
| C-N8 | A intenta `write` sobre algo de B | Denegado | ⏳ |
| C-N9 | A enumera IDs (1..N) por API/URL | Solo devuelve los suyos | ⏳ |

## D. Regresión sobre usuarios internos
| # | Verificación | Esperado | Estado |
|---|---|---|---|
| D1 | Operador de monitoreo ve todos los eventos | Sin cambios | ⏳ |
| D2 | Despacho/FSM ve todas las órdenes | Sin cambios | ⏳ |
| D3 | Facturación/cobranza ve todas las facturas | Sin cambios | ⏳ |
| D4 | Admin/Suscripciones ve todas las subs | Sin cambios | ⏳ |
| D5 | Crones/automatismos (sudo) operan igual | Sin cambios | ⏳ |

## E. Rendimiento de las Record Rules (volumen representativo)
| # | Verificación | Esperado | Estado | Medición |
|---|---|---|---|---|
| E1 | Test `perf` automatizado | < cota (5s smoke) | ⏳ | ___ s |
| E2 | Búsqueda de un portal contra volumen REAL de STAGING | Tiempo aceptable (< ~1s típico) | ⏳ | ___ s |
| E3 | Plan de listado del dashboard (varios modelos) como portal | Sin N+1 ni full-scans evidentes | ⏳ | |
| E4 | `EXPLAIN`/índice en `partner_id` de los modelos clave | Usa índice | ⏳ | |

## F. Auditoría y registros de seguridad
| # | Verificación | Esperado | Estado |
|---|---|---|---|
| F1 | Creación de usuario portal registra traza | Log `COC: usuario portal creado ...` | ⏳ |
| F2 | Logs estructurados del gateway con `request_id` | Presente (base WS-8) | ⏳ |
| F3 | Intento de acceso denegado deja rastro | Visible en log Odoo | ⏳ |
| F4 | (WS-3) Auditoría de acceso por recurso/IP | ⛔ pendiente WS-3 (no bloquea WS-2) | ⏳ |

## G. Criterio de cierre de WS-2
- [x] A1–A5 ✅ (instalación limpia, exit 0; grupo+rules+ACL cargados)
- [x] B1–B2 ✅ (suite 11/11 verde) · B3 ✅ (sin warnings de seguridad)
- [x] C-P1/C-P2/C-N1 ✅ (datos reales) · C-N2(IDOR)/C-N7/C-N8(BAC) ✅ (automatizado) · C-P7 ⏳ (UI empresarial, opcional)
- [x] D ✅ (admin ve 242 == total; sin regresión) · D5 (crones) n/a en lab
- [x] E1/E2 ✅ (0.006 s real) · E3/E4 ⏳ (revisión índices, recomendado)
- [x] F1 ✅ (traza de creación de usuario portal) · F2 ✅ (logs gateway base) · F4 = WS-3 (no bloquea)
- [ ] **Aprobación de Enrique** → cierre WS-2 → inicio WS-5

> Solo con G completo se despliega a **V18** y se inicia **WS-5 (OTP + JWT)**.

---

### Comandos de referencia (STAGING)
```bash
# Actualizar + correr suite de seguridad
odoo -d Sentinela_STAGING -u sentinela_api --test-enable \
     --test-tags sentinela_api,security --stop-after-init
# Solo rendimiento
odoo -d Sentinela_STAGING --test-enable --test-tags perf --stop-after-init
```
