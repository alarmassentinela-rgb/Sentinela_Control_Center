# UAT — Cobro Adelantado Global del Cliente

**Módulo:** `sentinela_subscriptions` `18.0.1.4.30` · **Entorno:** STAGING (NO producción)
**Acceso:** http://192.168.3.2:8075 · **DB:** `Sentinela_STAGING` · sin crones automáticos
**Objetivo:** aceptar el feature en interfaz gráfica antes de autorizar el `-u` en V18.

> Cliente de ejemplo sugerido: **EDGARDO AROLDO GARCIA VILLANUEVA** (id 20755), tiene 2 suscripciones de MONITOREO. Sirve para casi todos los pasos. Para el paso 4 (intervalos mixtos) cambia la **Frecuencia de Cobro** de una de sus subs a *Trimestral* (un clic en el form de la sub) o usa cualquier cliente con frecuencias distintas.

## Checklist (marca cada uno)

| # | Paso | Cómo | Resultado esperado | OK |
|---|------|------|--------------------|----|
| 1 | Abrir wizard desde una **suscripción** | Suscripción activa → header → botón **"Adelanto Global Cliente"** | Abre el modal "Cobro Adelantado Global del Cliente" con el cliente precargado | ☐ |
| 2 | Abrir wizard desde un **cliente** | Contacto → pestaña fiscal, grupo "Condiciones de Pago y Facturación" → botón **"Cobro Adelantado Global"** | Mismo modal, mismo cliente precargado | ☐ |
| 3 | Preview claro y legible | En el modal, con "Ciclos a adelantar" = 1 | Tabla con una fila por suscripción: Plan, Intervalo, Ciclos, Meses, **Próx. cobro ACTUAL**, **Próx. cobro TRAS adelanto**, Importe; Total y nº de suscripciones arriba | ☐ |
| 4 | Aviso de **intervalos mixtos** | Cliente con subs de distinto intervalo (p.ej. una Mensual y una Trimestral) | Banda **amarilla** de advertencia + la columna "Próx. cobro TRAS adelanto" difiere por sub (cada una avanza N × su intervalo) | ☐ |
| 5 | Factura adelantada de **1 ciclo** | Ciclos = 1 → **Generar Factura Borrador** | Se abre UNA factura borrador con todas las subs; tipo Cobro Adelantado; Ciclos adelantados = 1 | ☐ |
| 6 | Factura adelantada de **varios ciclos** | (otro cliente o tras revertir) Ciclos = 3 → Generar | Factura borrador con cantidades × 3 / periodo de 3 ciclos | ☐ |
| 7 | **Publicar** y confirmar fechas | En la factura borrador → **Confirmar/Publicar** | Cada suscripción: "Próximo Cobro" avanza N×intervalo; en el chatter de cada sub aparece el mensaje "Cobro adelantado global…" | ☐ |
| 8 | **Cron** ya no re-factura | Revisa la(s) sub(s): su "Próximo Cobro" quedó en el futuro | El barrido de facturación no las toma hasta la nueva fecha (su `next_billing_date` ya pasó al futuro) | ☐ |
| 9 | **Bloqueo de concurrencia** | Con un adelanto del mismo cliente aún sin pagar/cancelar, intenta crear otro | `UserError`: "Ya hay un cobro adelantado global EN CURSO para…" | ☐ |
| 10 | **Reversa total** al cancelar | En la factura de adelanto → Restablecer a borrador / Cancelar | Cada suscripción regresa EXACTAMENTE a su fecha original; chatter "Adelanto global revertido…" | ☐ |

## Notas
- Todo esto es STAGING; las facturas y cambios de fecha aquí no afectan producción.
- La **presentación** de la factura sigue la preferencia del cliente: `global` → líneas consolidadas; `individual`/`by_branch` → una línea por suscripción. Siempre es **una sola factura**.
- **V1:** la reversa es **solo total** (cancelar la factura completa). Las notas de crédito sobre un adelanto global se bloquean a propósito.

## Resultado UAT
- [ ] **APROBADA** — proceder a preparar plan de despliegue a producción.
- [ ] **Observaciones:** _____________________________________________
