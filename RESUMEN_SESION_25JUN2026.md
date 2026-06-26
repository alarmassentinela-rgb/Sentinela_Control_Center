# Resumen de sesión — 25 de junio de 2026

Sesión enfocada en **arrancar el timbrado fiscal automático** (CFDI vía Prodigia) para
reemplazar a MASadmin, con una **prueba REAL controlada (Rocío Calderón)** antes del
estreno masivo del 1-jul, más dos reportes/verificaciones programadas.

---

## 1. Cron de auto-timbrado CFDI (acotado a facturas NUEVAS)
Base creada la noche del 24-jun (commits `ea97a9b` + `290329c`, v18.0.1.2.0):
- `account.move._cron_auto_stamp_prodigia()` + cron `ir_cron_auto_stamp_prodigia` (account.move, horario, **nace desactivado**, noupdate).
- Triple salvaguarda: gate `auto_stamp_enabled`, corte `invoice_date >= auto_stamp_cutoff` (2026-06-25), y solo `out_invoice/posted/cfdi_status='pending'/sin UUID`.

## 2. Correo de la factura DESPUÉS de timbrar (no al generar)
Detectado: el cron de generación enviaba el correo a las 07:00 (antes del timbrado 08:00) → el cliente recibía el PDF como **remisión sin timbre**. También: el template `account.email_template_edi_invoice` **no trae el reporte adjunto** (no mandaba PDF).
- **subscriptions v18.0.1.4.7** (`6e6d834`): `_billing_generate_invoice` NO envía correo al generar si `requiere_factura` (esos van tras timbrar). Remisiones siguen enviándose al generar.
- **cfdi_prodigia v18.0.1.2.3** (`6e6d834`+`c51a511`): nuevo `_cfdi_send_invoice_email()` que **renderiza el PDF** (`account.account_invoices` = reporte CFDI) y adjunta **PDF + XML** timbrado, con CC (cliente + suscripción). El cron lo llama tras timbrar OK. PDF verificado renderiza en cron (119KB).
- Desplegado STAGING + PROD (cargas limpias).

## 3. Prueba REAL con Rocío Calderón (SUB-0262) — armada para mañana 26-jun
- Enrique movió `next_billing_date` de SUB-0262 a **26-jun** para usarla de prueba real.
- Datos fiscales validados: receptor ROCIO DE CRISTAL CALDERON SEGURA (RFC CASR7612185WA, CP 87300, régimen 612, uso G03); emisor ENRIQUE GARZA CANTU GACE680421P37. Estructura correcta: **fiscal** (partner 25339) + **domicilio de servicio** (`service_address_id` = /CASA 26047, hijo). No es duplicado.
- **Prodigia validado** (timbres + CSD cargados por Enrique): prueba con `prueba=true` devolvió UUID, revertida → integración OK (auth, contrato, XML aceptado).
- **Activado para mañana:** `test_mode=False` (REAL), `auto_stamp_enabled=1`, cron **activo** (nextcall 26-jun 08:00). Solo Rocío califica (corte ≥25-jun).
- Flujo 26-jun: 07:00 genera factura fiscal (pending, posted, sin correo) → 08:00 timbra REAL + envía PDF+XML a rociodecristal@gmail.com.
- **Remisión de junio de Rocío** (INV/2026/00032, $650, pagada): se **deja intacta** por decisión de Enrique (tendrá 2 docs de junio a propósito).

## 4. Verificaciones / reportes programados (server-side, por LAN)
Cloud no alcanza 192.168.3.2 → todo corre como cron en el propio server + Telegram.
- **Verificación de Rocío:** `/home/egarza/verify_rocio_timbrado.sh`, cron one-shot `40 8 26 6 *` (se auto-elimina). Manda a TG de Enrique (7965190381) el veredicto del timbrado (OK real / prueba / pendiente / error), con UUID, total, correo.
- **Reporte diario a Irma Bedolla** (cobranza, TG chat 8548520035, bot Sentinela): `/home/egarza/reporte_diario_facturas.sh`, cron `0 9 * * *`. Lista remisiones + facturas fiscales generadas ese día (nº factura, sub, cliente, monto), con totales y chunking. Probado enviando a Enrique (200 OK).

## Hallazgos
- **Ninguna sub se timbra en junio (25-30):** las 10 que facturan son de clientes "no timbrar" (remisión). Los 179 que requieren factura cobran **1-jul en adelante** (105 el 1-jul) → ese es el estreno real del cron.
- **Sistémico:** 11 facturas de junio (1-10 jun) salieron remisión pese a `requiere_factura=True` (flag activado tarde). De 1-jul en adelante ya saldrán bien como fiscales.

## Pendientes
1. **Mañana 26-jun:** confirmar (por el mensaje automático ~08:40) que Rocío se timbró **REAL** (UUID no "modo de pruebas", con sello/QR) y le llegó el correo con PDF+FACTURA + XML.
2. **1-jul:** vigilar el estreno masivo (~105 facturas fiscales). Si la prueba de Rocío salió bien, debería fluir.
3. **Remisiones (no fiscales):** su correo se envía con el template estándar que **NO adjunta PDF** → el cliente no recibe documento. Decidir si también se les adjunta el PDF.
4. **11 facturas de junio** en remisión pese a requerir factura: decidir si se reexpiden como fiscales o junio queda en remisión.
5. (Pendientes previos siguen: TAOS/Mercedez GPS fijar posición, filtro zeroCoordinates Traccar.)

> Nota: en el repo aparecen también `b12edfb` (remitente cobranza@ en plantillas) y `b63e11f` (manual PDF de envío de correos) — trabajo de correos ajeno a esta sesión de timbrado.

---

# Sesión vespertina — Migración GPS KAWAC CONSTRUCCIONES → SentiCar

Operación de datos en PROD (sin cambios de código): mover la flota GPS de **KAWAC
CONSTRUCCIONES** de la plataforma **Smake** a **SentiCar** (Traccar). "Kawac" resultó ser
el **cliente**, no una plataforma.

## 1. Consolidación en Odoo (52 equipos)
- **SUB-0395** (KAWAC, plataforma Smake, draft) tenía los **52 GPS reales** (revolvedoras, volteos, trailers…), todos `senticar_id=0/pending`.
- **SUB-0436** (KAWAC, mismo partner 21517, plataforma SentiCar, active) solo tenía 3 equipos de prueba.
- Se **reasignó `subscription_id`** de los 52 equipos: SUB-0395 → SUB-0436 (vía XML-RPC, `api_user`). Como `gps_platform` del equipo es `related` de la sub, quedaron en `senticar` solos. SUB-0436 quedó con **55** (52 + 3 prueba).
- **SUB-0395 cerrada** (`state=cancelled`, `technical_state=cut`, con nota de migración). Quedó vacía.
- ⚠️ El wizard `transfer_to_subscription` NO sirve aquí: bloquea a propósito mover entre plataformas distintas (smake→senticar). Por eso se reasignó el `subscription_id` directo.

## 2. Alta en Traccar/SentiCar
- `action_register_senticar` sobre los 52 → **55/55 registrados**, ids únicos, sin duplicados.
- ⚠️ Trampa: el alta lanza un `Fault` XML-RPC al final del request, **pero el `senticar_device_id` ya commitea** (los servicios SentiCar hacen commit interno) → quedó OK. Verificado por separado: 55 ids, `senticar_sync_msg='Registrado y activo'`.
- Cliente con visibilidad: usuario `kawac.construcciones@gmail.com` (senticar_user_id 21), grupo compartido.

## 3. Cutover físico por SMS (floLIVE)
- Comando GT06/Concox: **`SERVER,1,gps.senticar.com,5023,0#`** (modo 1=dominio, puerto Traccar GT06=5023). Plantilla `sentinela.gps.command.template` brand=concox_gt06/set_server.
- **Piloto** (Revolvedora #11): conectó a SentiCar en **~1 min** (status offline→online en Traccar). Comando validado end-to-end.
- **Lote:** de 45 equipos reales con SIM nuestra → **39 SMS enviados OK**. Verificado en Traccar: **32 ya reportando** (online) al cierre. Los 7 restantes enviados aterrizarán al encender.

## 4. Diagnóstico de las 6 SIMs con error + 7 sin ICCID
- **4× error 403 floLIVE = SIM en estado `SUSPEND`** (confirmado con `get_sim_diagnostics`; floLIVE rechaza SMS a SIM suspendida): REVOLVEDORA #10 (~20 meses sin conectar, prob. muerta), BOMBA #3, "No vehiculo.", Volteo #14 (suspendida apenas 12-jun, prob. viva).
- **2× SIM no hallada en floLIVE** = ICCID malformado/corto en Odoo (17–18 díg vs 19): Volteo #37, "No vehiculo".
- **7× sin ICCID** (SIM del cliente o no registrada): no se reconfiguran por SMS desde aquí.
- **Decisión de Enrique:** NO reactivar ninguna SIM por ahora.

## Verificación
- Traccar API directo: `http://192.168.3.2:8082` (user `odoo@sentinela.com.mx`, pass en `ir.config_parameter sentinela.traccar_api_password`). 32 KAWAC online confirmados.

## Pendientes (migración KAWAC)
1. **4 SIMs suspendidas** — decidir reactivación (re-genera cobro de datos). REVOLVEDORA #10 casi seguro retirada.
2. **2 ICCID malformados** — corregir el ICCID en Odoo y reenviar SMS.
3. **7 sin ICCID** — capturar SIM/reconfigurar a mano en campo.
4. Las 7 unidades enviadas que aún no reportan: confirmar que entran al encender.

> Memoria: `project_kawac_migracion_senticar.md` (nueva) + línea en `MEMORY.md`. Sin cambios de código → no hubo release ni deploy de módulo.
