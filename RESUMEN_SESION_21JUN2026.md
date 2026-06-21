# Resumen de Sesión — 21 de junio de 2026

Continuación de pendientes de FSM (ventas/orden) + recuperación de teléfonos de la
migración + feature grande: **encuesta de satisfacción con rifa**. Todo en `sentinela_fsm`
(salvo la recuperación de datos, que tocó `res.partner` en V18). Desplegado y verificado.

---

## 1. Ventas / Orden FSM — pendientes cerrados

### 1.1 `v18.0.1.10.4` (commit 605f9db) — Dirección de factura filtrada
`partner_invoice_id` en ventas tenía domain vacío (mostraba todo el catálogo). Mismo fix
que la de entrega: `domain="[('id','child_of',partner_id)]"` en `sale_order_views.xml`.

### 1.2 `v18.0.1.10.5` (commit a989ded) — Teléfono con fallback a móvil
El `phone` de la orden pasó de `related('partner_id.phone')` a **computed/stored**:
`partner_id.phone or partner_id.mobile`. Arregla el campo vacío en form, reporte y botón
de llamada del portal técnico cuando el número está en *Móvil*. Probado (Abel Cavazos).

### 1.3 `v18.0.1.10.6` (commit d6f2f8b) — Plantillas manuales versionadas
Las 12 plantillas de checklist creadas a mano (sin xml_id) se versionaron en
`data/fsm_checklist_templates.xml`. **TRAMPA evitada:** agregarlas con xml_id nuevo
duplicaría en el `-u`. Solución: pre-vincular cada xml_id al registro vivo (por nombre,
`noupdate`) en STAGING+PROD **antes** del `-u`. Verificado: total se mantuvo en 56, 0 sin
xml_id. Si se reinstala el módulo desde cero, ahora se recrean solas.

### 1.4 `v18.0.1.10.7` (commit 0b0ddf3) — Calendario muestra el cliente
El calendario/agenda solo mostraba el folio (OS-00019). Override de `_compute_display_name`
→ `"OS-#### - CLIENTE"` (el calendario usa display_name como título). Visible también en
selectores y enlaces. Verificado OS-00019 / OS-00041.

---

## 2. Recuperación de teléfonos (migración) — dato faltante, no bug

Al investigar "la orden no trae el teléfono" (OS-00041), se confirmó que **no es bug**: el
campo ya jala teléfono o móvil cuando existen. El problema es **dato faltante**: **159 subs
activas / 125 clientes (43%) sin teléfono ni móvil** en Odoo (hueco de la migración).

- Crucé los 125 contra los CSVs de migración del repo:
  - **WISP/Internet** → `clientes_argus_LIMPIO.csv` por **nombre** → 42 recuperados.
  - **Alarma** → Securithor tiene los teléfonos pero por `OBJECTNUMBER`, y las **cuentas de
    monitoreo se renumeraron en la migración** (consecutivas 4 díg) → se perdió la llave →
    solo 1 match por nombre.
- **Aplicados 43 teléfonos a PROD** (escritos en `partner.phone`, solo donde estaba vacío,
  0 pisados). Formato `+52 AAA BBB CCCC`. Incluye OS-00041 (Juan Antonio Rodríguez Meza →
  `+52 868 304 4413`). Subs sin teléfono: **159 → 115**.
- **Quedan ~82 sin match** (55 alarma + 25 internet + 2 dominio). Los 55 de alarma necesitan
  un **export nuevo de Securithor por titular** o reconstruir el mapeo cuenta-Odoo↔OBJECTNUMBER.

---

## 3. `v18.0.1.11.0` + `.11.1` — Encuesta de satisfacción + Rifa (feature nuevo)

Idea de Enrique: que la orden finalizada que le llega al cliente traiga una liga de encuesta
para evaluar al técnico, con un incentivo (rifa) para motivar a llenarla.

**Qué se construyó:**
- **Liga pública** `/encuesta/<token>` (token por orden, generado en create + lazy en
  órdenes viejas). Página móvil: ⭐⭐⭐⭐⭐ para el técnico + comentario. Controlador
  `controllers/survey_portal.py`, plantillas `views/survey_templates.xml`.
- Al responder (`register_survey_response`): guarda `customer_rating`/`customer_feedback` +
  asigna **boleto `RIF-#####`** (secuencia nueva). **1 boleto por orden** (token de un solo
  uso = anti-spam). Alimenta el tablero "Análisis de Desempeño".
- **Se premia por LLENARLA, no por la calificación** (honestidad; el boleto se da sin
  importar las estrellas).
- **Canales (los 3):** botón en el **correo** de reporte, mensaje por **Telegram** al cliente
  (`partner.send_telegram_message`, respeta `notification_channel`), y **QR en el PDF** del
  reporte (`/report/barcode/`).
- **Rifa:** wizard `sentinela.fsm.raffle.draw.wizard` ("Rifa: Sortear Ganador", random por
  rango de fechas, marca `raffle_won`) + vista "Rifa: Participaciones", bajo Reportes y
  Análisis (group_fsm_manager).
- **Disparador:** `action_send_report_to_customer` (requiere reporte autorizado por operador).

**Fix latente (`.11.1`):** ese método usaba la firma vieja de `_render_qweb_pdf` (Odoo 18
pide `report_ref` primero) → el envío de reporte estaba roto desde antes. Corregido.

**Verificado end-to-end (STAGING + PROD):** form HTTP 200, submit guarda boleto, anti-doble
voto, QR image/png 200, PDF renderiza con QR (127 KB), sorteo elige ganador.

---

## Estado de despliegue
Todo en producción **V18** y verificado:
- `sentinela_fsm` → **18.0.1.11.1**
- `sentinela_subscriptions` → **18.0.1.4.6** (cambios de otra sesión, no de hoy)

Web reiniciado donde hubo cambios de Python/controllers. Tags por release en GitHub.

---

## Pendientes para la próxima
1. **Encuesta automática al finalizar** la orden vs. el flujo actual (autorizar + enviar
   reporte). Enrique lo decide; es un ajuste chico.
2. **Premio + periodicidad** de la rifa (mensual sugerido) — operativo, sin código.
3. **Recuperar los 55 teléfonos de alarma** — requiere export de Securithor por titular o
   mapeo cuenta-Odoo↔OBJECTNUMBER.
4. Para el canal **Telegram**, el cliente debe estar vinculado al bot (los demás reciben
   correo + QR igual).
5. (Viejos) ¿quitar sub-filtro "Activos" de Tráfico en monitoring?; SMS al cliente (falta gateway).
