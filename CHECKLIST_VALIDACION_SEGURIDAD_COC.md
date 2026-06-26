# Checklist de Validación de Seguridad — Portal COC (WS-2)

> **Evidencia de aceptación del Sprint.** Cierre de WS-2 condicionado a TODOS los ítems en ✅.
> Entorno de validación: **STAGING** (`Sentinela_STAGING`, contenedor `odoo-lab`, `:8075`).
> Estado global: ⏳ EN VALIDACIÓN · Responsable: ____ · Fecha: ____

Leyenda estado: ✅ pasa · ❌ falla · ⏳ pendiente · ⛔ bloqueante.

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
- [ ] A1–A5 ✅ (instalación limpia)
- [ ] B1–B3 ✅ (suite verde)
- [ ] C-P1..P7 y C-N1..N9 ✅ (aislamiento manual)
- [ ] D1–D5 ✅ (sin regresión interna)
- [ ] E1–E4 ✅ (rendimiento aceptable)
- [ ] F1–F3 ✅ (auditoría base; F4 = WS-3, no bloquea)
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
