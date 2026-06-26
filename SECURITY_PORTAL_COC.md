# SECURITY_PORTAL_COC — Aislamiento de datos del Portal COC (WS-2)

> Entregable de seguridad del Sprint 0. Objetivo: **ningún cliente puede acceder, directa o indirectamente, a información de otro cliente**, aunque exista un bug en el Gateway o en un endpoint.
> Versión 1.0 · 2026-06-26.

## 1. Modelo de seguridad en capas (defensa en profundidad)

| Capa | Mecanismo | Garantía |
|---|---|---|
| **1ª línea (datos)** | **Record Rules de Odoo** sobre el grupo `group_coc_portal` | Aunque el endpoint/gateway falle, Odoo NO devuelve registros fuera del alcance del cliente. |
| 2ª línea (acceso) | **ACL** read-only del grupo portal | El cliente no puede escribir/crear/borrar donde no debe. |
| 3ª línea (identidad) | **Gateway** (JWT, usuario portal lazy, scopes por rol/sucursal) | Autenticación y alcance fino; **nunca sustituye** las record rules. |
| 4ª línea (auditoría) | Log de acceso (WS-3) | Trazabilidad de quién accedió a qué. |

**Principio rector:** el Gateway corre **como el usuario portal** del cliente (creado lazy en el primer login). Así las record rules de Odoo se aplican nativamente — son la primera línea de defensa, no un complemento opcional.

## 2. Grupo y alcance

- **Grupo:** `sentinela_api.group_coc_portal` (implica `base.group_portal`).
- **Usuario portal lazy:** `res.users._coc_ensure_portal_user(partner)` — creado en el primer login, vinculado al `res.partner`, login sintético (auth real en el Gateway).
- **Dominio de aislamiento (record rules):** `partner_id child_of user.partner_id.commercial_partner_id` →
  - Residencial: ve solo su propio partner.
  - Empresarial: ve su entidad comercial + sucursales (techo); el **alcance fino por sucursal/rol lo aplica el Gateway por encima** de este techo.

## 3. Matriz de permisos — capa Odoo (por modelo × grupo)

| Modelo | `group_coc_portal` (cliente) | Personal interno | Record rule (aislamiento) |
|---|---|---|---|
| `sentinela.subscription` | **R** | RWCU | ✅ partner child_of commercial |
| `sentinela.alarm.event` | **R** | RWCU | ✅ partner child_of commercial |
| `sentinela.monitoring.device` | **R** | RWCU | ✅ partner child_of commercial |
| `sentinela.fsm.order` | **R** (create con su endpoint, Sprint 2) | RWCU | ✅ partner child_of commercial |
| `sentinela.sign.document` | **R** (firma vía sudo + token) | RWCU | ✅ partner child_of commercial |
| `account.move` | **R** (heredado de portal) | RWCU | ✅ out_invoice/refund/receipt + partner child_of commercial |

R=read · W=write · C=create · U=unlink. En v1 el cliente es **solo lectura** (alineado con "Facturación solo consulta" y exposición de datos). Los permisos de escritura puntuales (crear ticket FSM, firmar documento) se habilitan con su endpoint y sus pruebas.

## 4. Matriz de permisos — capa Gateway (por rol × módulo)

> El alcance por **rol** y por **sucursal** se aplica en el Gateway (scopes en JWT), SObre el techo de las record rules. Roles extensibles sin tocar lógica.

| Módulo / Capacidad | Titular (Admin) | Operador-Flotilla | Contabilidad | Solo Lectura |
|---|:--:|:--:|:--:|:--:|
| Servicios / Dashboard | ✅ | ✅ (flotilla) | ✅ (finanzas) | 👁️ |
| Seguridad / Alarma | ✅ | — | — | 👁️ |
| Internet | ✅ | — | — | 👁️ |
| GPS / Flotilla | ✅ | ✅ | — | 👁️ |
| Facturación / CFDI | ✅ | — | ✅ | 👁️ |
| Soporte / Tickets | ✅ | ✅ (sus servicios) | — | 👁️ |
| Reportes | ✅ | ✅ (flotilla) | ✅ (finanzas) | 👁️ |
| Administración (usuarios/sucursales) | ✅ | — | — | — |
| **Alcance por sucursal** | todas | limitable | todas | limitable |

👁️ = solo lectura. **Importante:** este filtrado de rol/sucursal es la 3ª línea; aun si fallara, la 1ª línea (record rules) impide ver datos de **otro cliente**.

## 5. Casos de prueba (implementados en `sentinela_api/tests/test_security_isolation.py`)

| ID | Tipo | Caso | Esperado |
|---|---|---|---|
| TC-S-POS1 | Positivo | Cliente A lista sus documentos | Ve doc_a, no doc_b |
| TC-S-NEG1 | Negativo | A busca por id de doc de B | Resultado vacío |
| TC-S-IDOR | IDOR | A hace `browse(doc_b).read()` | `AccessError` |
| TC-S-BAC1 | Broken Access Ctrl | A intenta `write()` (incluso sobre lo suyo) | `AccessError` (read-only) |
| TC-S-BAC2 | Broken Access Ctrl | A intenta `unlink()` | `AccessError` |
| TC-S-RULE | Estructural | Existe record rule con filtro `partner_id` para los 6 modelos | Presente |
| TC-S-ACL | Estructural | ACL del grupo COC es read-only en los 4 modelos propios | `write/create/unlink = 0` |
| TC-S-USER1 | Identidad | Usuario lazy tiene grupos correctos y es `share` | OK |
| TC-S-USER2 | Identidad | Creación lazy es idempotente | No duplica usuario |

**Cobertura funcional:** anclada en `sentinela.sign.document` (creable con mínimos campos). **Cobertura estructural:** los 6 modelos expuestos. Al construir el endpoint de cada modelo se añaden pruebas funcionales con su fixture específico (mismo patrón A-no-ve-B).

## 6. Escenarios OWASP cubiertos

- **A01 Broken Access Control / IDOR:** record rules + ACL read-only + prueba de `browse(id_ajeno)`.
- **Aislamiento multi-tenant lógico:** dominio `child_of commercial_partner_id`; el Gateway nunca amplía el techo.
- **Privilege escalation (write):** ACL read-only bloquea mutaciones del lado del cliente.
- **Pendiente WS-5 (auth):** fuerza de OTP/JWT, rate-limit, fijación de sesión — se prueban en su bloque.

## 7. Reporte de validación — ESTADO

| Ítem | Estado |
|---|---|
| Implementación (grupo, usuario lazy, record rules, ACL, tests) | ✅ Completa (código) |
| `py_compile` / XML bien formado | ✅ Verificado local |
| Instalación `-u` en STAGING (`Sentinela_STAGING` :8075) | ⏳ **Pendiente** (deploy) |
| Ejecución de la suite `--test-enable --test-tags security` en STAGING | ⏳ **Pendiente** |
| Verificación manual (login como portal A, intentar ver B) | ⏳ **Pendiente** |
| No regresión: usuarios internos conservan acceso | ⏳ **Pendiente** (verificar en STAGING) |
| Despliegue a producción V18 | 🚫 **Bloqueado** hasta superar TODO lo anterior |

### Cómo validar en STAGING
```
# deploy del addon a STAGING (skills) y correr tests de seguridad:
odoo -d Sentinela_STAGING -u sentinela_api --test-enable --test-tags sentinela_api,security --stop-after-init
```
Criterio de paso: **todos los TC-S en verde** + verificación manual (un portal no ve datos de otro) + sin regresión interna. Solo entonces se procede a V18 y a WS-5.

## 8. Notas / pendientes
- Verificar en STAGING que las record rules existentes de `monitoring.device` (2) y `fsm.order` (3) no entran en conflicto (se combinan por OR entre grupos distintos; el cliente portal no pertenece a los grupos internos).
- `account.move` y `sign.document` heredan lectura de `base.group_portal`; la record rule COC añade el filtro de aislamiento para el grupo COC.
- Cuando se habiliten escrituras (crear ticket, firmar), añadir ACL puntual + pruebas funcionales de que A no puede crear/firmar sobre recursos de B.
