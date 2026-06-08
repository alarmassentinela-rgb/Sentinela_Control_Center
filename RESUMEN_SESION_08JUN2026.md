# Resumen de sesión — 8 de junio de 2026

Sesión larga centrada en **diseño de factura/remisión CFDI**, más operación WISP (Argus/SUB-0346), prueba de facturación, lab de staging y diagnóstico de conexiones dedicadas.

---

## 1. SUB-0335 — "¿por qué no se generó su factura?"
- **Causa:** no fue un error. Las **crons de facturación están congeladas** (freeze de migración): `Generar Pre-Facturas` (id 39), `Auto-Suspender` (55), `Recordatorios` (56), `Prórrogas` (40), `Leasing` (57) — todas OFF.
- Mientras estén apagadas, **ninguna** sub factura automático aunque su `next_billing_date` caiga hoy. Go-live ≈ **1-jul** (reactivar crons).

## 2. SUB-0346 (cta0207) — suspendido, ya pagado, no se reactivaba
- **Culpable: Argus Black** (no Odoo). Metió al cliente al walled-garden el 6-jun (perfil `argusblack_servicio_suspendido`).
- El pago se registró en **Odoo**, que Argus no ve (facturación separada); y el reconciliador de Argus está apagado → nadie lo levantaba.
- **Fix manual** en CCRsentinela: perfil del secret → `argusblack_plan_841_1799` (su plan 20/7), quitar de walled-garden, tirar la sesión. **Reactivado y navegando.**
- ⚠️ Quedan **~6 cuentas más** en `argusblack_servicio_suspendido` por auditar (pueden estar pagadas en Odoo). **Pendiente:** correr `reconcile_ccr_all.py`.

## 3. Prueba de facturación SIN timbrar y SIN correo
- A pedido de Enrique: generar pre-facturas/remisiones para probar, sin timbrar ninguna.
- Corrida manual del cron oficial `_cron_generate_pre_invoices()` apagando `auto_send_mail` en las 228 subs (0 correos, restaurado después).
- **12 remisiones generadas y posteadas** (INV/2026/00058→00069), 0 timbradas, 0 correos.
- ⚠️ El cron **avanzó su `next_billing_date` a julio** → al go-live el candado anti-duplicado evita re-facturarlas. Quedaron un ciclo adelante del resto.

## 4. Argus — estado confirmado
- Cutover del 3-jun **sigue firme**: túnel `argusblack` OFF, 8 schedulers de cliente OFF, auth **local** (`use-radius=false`), `sync_active=True`. **Odoo es el único jefe de suspensiones.**
- Lo único de Argus vivo: schedulers de **failover de ISP/ruteo** (redundantes con el Balanceador). **Decisión: dejarlos por ahora** (apagarlos toca ruteo, requiere backup del CCR).

## 5. 🧪 Lab / Staging accesible por navegador
- Producción tiene `dbfilter = ^Sentinela_V18$` → bloquea entrar a STAGING por el login normal.
- **Montado contenedor `odoo-lab`** (puerto 8075, DB Sentinela_STAGING, sin crons) → `http://192.168.3.2:8075`, login `egarza@sentinela.com.mx` / `dea2113.`. Producción intacta.
- **Quedó APAGADO** al cierre (`docker stop odoo-lab`). Reencender: `docker start odoo-lab`. Doc en memoria `reference_lab_staging_access.md`.

## 6. 🧾 Rediseño de Factura / Remisión CFDI (`sentinela_cfdi_prodigia`)
Plantilla `report_invoice.xml` (vista `report_invoice_cfdi_section`). **Una sola plantilla** sirve para remisión (sin `cfdi_uuid`) y factura timbrada (con `cfdi_uuid`). Se trabajó iterando en el lab y verificando con renders PDF reales. Versión final: **v18.0.1.1.14**.

Cambios (en orden):
1. **Título dinámico:** "REMISIÓN" si no timbrada, "FACTURA" si timbrada.
2. **Logo** centrado, con margen, tamaño correcto (antes desbordaba la celda).
3. **IVA dinámico** en totales (8% frontera / 16%), antes hardcodeado 16%.
4. **Encabezado** migrado de `<table>` a `divs display:table-cell` → elimina rejillas grises de wkhtmltopdf. Datos de la empresa más grandes.
5. **Datos fiscales completos:** Caja del documento con Referencia Interna (antes "Folio"), Fecha de Emisión (antes "Fecha"), Folio Fiscal (UUID en un renglón), Fecha de Certificación, Serie Cert. SAT, Serie Cert. Contribuyente.
6. **Recuadro "CONDICIONES DE LA VENTA"** (entre Total y Timbre): Condiciones de Pago, Método de Pago (PUE), Forma de Pago, Lugar de Expedición, Uso de CFDI, Tipo de Comprobante, Exportación.
7. **Importe con letra** + "NN/100 M.N." + "Moneda: MXN Pesos Mexicanos" (junto a totales).
8. **Emisor = nombre legal** `ENRIQUE GARZA CANTU` (persona física, vía `company.l10n_mx_edi_fiscal_name`) en vez de la marca "Sentinela" (que queda en el logo). **Coincide con el Nombre que ya manda el XML del CFDI.**
9. **Receptor:** Tel + Email del cliente debajo de Régimen Fiscal; se quitó "Uso CFDI" de aquí (ya está en Condiciones).
10. **Timbre Fiscal limpio:** solo Sello CFDI, Sello SAT, Cadena Original + QR; sin rejillas ni recuadros azules. Los sellos largos **se ajustan solos** (verificado con sellos de muestra).
- **Bug de datos arreglado:** el estado de la empresa apuntaba a "Өмнеговь" (¡provincia de Mongolia!) → corregido a **Tamaulipas** (id 513).
- ⚠️ El **timbrado CFDI (XML/SAT) NO se tocó** — solo la representación impresa. La factura timbrada conserva todo lo fiscal.
- Nota cosmética pendiente: el emisor sale en MAYÚSCULAS sin acento (coincide con SAT). Si se quiere "Enrique Garza Cantú" bonito, es otro cambio.

## 7. Diagnóstico de navegación para conexiones DEDICADAS (`sentinela_subscriptions` v18.0.1.3.84)
- La pestaña "Diagnóstico" / botón "Validar Navegación" estaba **hardcodeada a PPPoE** → reventaba en subs internet dedicadas (`internet_mgmt_mode=static`, IP fija sobre el Balanceador, sin PPPoE). Caso: **SUB-0307 = enlace FFW México** (IP 10.99.99.2).
- **Agregada rama dedicada** `_validar_navegacion_static`: lee la **simple queue** de la IP fija en el Balanceador (NO el conntrack de 14k entradas, que daba "no such item" por carrera). Veredicto: 🔴 SUSPENDIDO (queue disabled) / 🟢 NAVEGANDO (tasa>0, con Mbps) / 🟡 ENLACE ACTIVO sin tráfico. **100% lectura, no toca el enlace.**
- Probado en prod: 🟡 (queue `QoS_FFW_Mexico` habilitada, 0 Mbps en ese instante).
- Pendiente menor: el botón aparte "Tráfico en vivo" sigue PPPoE-only.

---

## Versiones desplegadas hoy (todo en V18 producción + pusheado a `main`)
- `sentinela_cfdi_prodigia`: 18.0.1.1.1 → **18.0.1.1.14** (rediseño factura/remisión)
- `sentinela_subscriptions`: 18.0.1.3.82 → **18.0.1.3.84** (candado mail ya estaba; diagnóstico dedicadas)
- Último commit: `abff279`

## PENDIENTES para mañana
1. **Auditar las ~6 cuentas en `argusblack_servicio_suspendido`** (correr `reconcile_ccr_all.py`) — pueden estar pagadas en Odoo y cortadas.
2. **SUB-0307 (FFW):** sigue en `draft`. Decidir: ¿Activar? ¿CFDI timbrado o solo remisión? (ver `project_ffw_alta_suscripciones`).
3. **Go-live facturación ≈1-jul:** reactivar crons 39/56/55/(57/40). Recordar que las 12 remisiones de hoy ya están un ciclo adelante.
4. (Opcional) emisor en formato bonito; `action_view_traffic` para dedicadas; apagar schedulers de ruteo de Argus (con backup del CCR).
5. El lab `odoo-lab` quedó apagado — reencender si se necesita.

## Memoria actualizada hoy
- NUEVA `reference_lab_staging_access.md` (acceso lab :8075)
- `project_migracion_wisp_argus_a_odoo.md` (estado Argus 8-jun + cta0207)
- `project_email_freeze_migracion.md` (prueba 12 remisiones)
- `project_ffw_alta_suscripciones.md` (diagnóstico dedicadas + setup Balanceador)
