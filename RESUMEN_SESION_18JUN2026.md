# Resumen de sesión — 18 de junio de 2026

## 1. Guía de Cobranza: aplicar un depósito a facturas de varios clientes (PDF a Telegram)
Pregunta de Enrique: cómo aplicar en Odoo un solo depósito de un cliente que paga sus
facturas **y** las de otro cliente (pago de tercero).

- **Respuesta/criterio:** en Odoo un pago pertenece a UN solo cliente/RFC. NO se puede un
  pago repartido. Solución = **un pago por cada cliente** (mismo diario de banco) +
  **una sola conciliación bancaria** que une el depósito contra ambos pagos. Si las
  facturas son PPD, cada pago lleva su propio Complemento de Pago (REP) por RFC.
- **Entregable:** `GUIA_COBRANZA_DEPOSITO_MULTICLIENTE.pdf` (script
  `gen_guia_deposito_multicliente.py`), 6 páginas, branding Sentinela, **5 capturas
  REALES** del STAGING: selección de facturas, wizard «Pagar», lista de pagos, tablero de
  bancos y la transacción del depósito en conciliación. Enviado a Telegram (v1→v3).
- **Para capturar:** se instaló Playwright + Chromium en WSL **sin sudo** (descarga de
  `.deb` con `apt-get download` + `dpkg-deb -x` a `/tmp/chromedeps/root` + `LD_LIBRARY_PATH`).
  Login STAGING `:8075` egarza/`dea2113.`. (ldpath guardado en `/tmp/chromedeps/ldpath.txt`.)
- **Hallazgo:** el Odoo es **Community con OCA (`om_account_followup`)** → **NO tiene el
  widget de conciliación de Enterprise**. La conciliación real = abrir la **transacción
  del banco** (línea de extracto) y ligar los pagos hasta `Importe residual = 0` /
  `Conciliado`. Para la captura se creó una línea de extracto demo en STAGING (BANORTE,
  $4,611.30) y se **borró** después (staging limpio). Nombres reales de clientes en las
  capturas: Enrique los dejó tal cual (sin anonimizar).

## 2. Limpieza de `default_code` con espacios sobrantes (PROD)
- Búsqueda por referencia (código Syscom = `default_code`) **sí funciona**; se detectó **1
  solo producto** con espacio al inicio: id 5302 `' SS-095-1H0'` → `'SS-095-1H0'`. Corregido
  en **prod (Sentinela_V18)**. 0 restantes, sin dobles espacios internos, sin colisiones.

## 3. Búsqueda por referencia en Almacén — aclaración (sin cambios)
- **No hay que instalar/habilitar nada.** El código Syscom vive en «Referencia interna» y
  las vistas de Inventario lo incluyen en el buscador (probado: Inventario→Productos,
  `001-A3010` → 1 resultado). Si "no se podía" era por estar en otra pantalla (Existencias),
  no ver la columna de referencia, o el filtro «Bienes». No requirió código.

## 4. ¿Módulo de bancos? — aclaración (sin cambios)
- No existe módulo "Bancos". Los bancos son **diarios** dentro de **Facturación** (`account`,
  ya instalado). Confirmados: BANORTE (00668059925) y HSBC (021818064871565017) + Bank/Cash.
  `accountant` (Enterprise) es uninstallable porque es Community. Nada que instalar.

## 5. Estudio de la API de Syscom + release `sentinela_syscom` v18.0.1.4.0 (EN PROD)
Se estudió la API **en vivo** con el token real de prod (ver memoria
`project_syscom_api_aprovechamiento`). Conclusión clave: la API es **solo de consulta**
(pedidos/carrito/listas dan 404 → la compra sigue manual) y la ficha `/productos/{id}`
regala datos que no se usaban (ficha técnica PDF, características, clave unidad SAT, etc).

**Cambios desplegados (v18.0.1.4.0, commits `42ac72d` código + `1d0ab70` docs):**
- **Opción B — no sobre-escribir existentes:** import y cron solo actualizan costo/stock/
  datos `syscom_*`/enriquecimiento; **respetan nombre, precio de venta, referencia,
  categoría e imagen**. `list_price` solo se fija en "rescate" (`<=1.0`). **Crítico:** el
  cron nocturno antes machacaba `list_price` cada noche — ya no.
- **Match por `syscom_id` O `default_code`** → no más duplicados de productos a mano.
- **Enriquecimiento:** campos nuevos en `product.template` (`syscom_sat_description`,
  `syscom_sat_unit_key` ej. H87, `syscom_caracteristicas` Html, `syscom_datasheet_url`),
  poblados por `_syscom_extract_enrichment()`; el wizard ahora pide la ficha de detalle.
- **Deploy verificado:** rsync → `-u` STAGING (exit 0) → `-u` V18 (exit 0) → restart web →
  HTTP 200. DB reporta `18.0.1.4.0`, los 4 campos existen en `product.template`.
- **CLAUDE.md** del módulo y **memoria** actualizados.

### Nota de credenciales (descubierta hoy)
XML-RPC a **prod** funcionó con `egarza@sentinela.com.mx` / **`Lcs1992`** en DB
`Sentinela_V18`. El password "rotado" `i8dl1QirG0p8DI#6` del índice de credenciales
**NO** autenticó por XML-RPC. (api_user uid=10 también entra pero sin permisos de contabilidad.)

## 3. Bot de Telegram para CLIENTES (@SentinelaAvisos_bot) — vinculación + rastreo + QR
Objetivo de Enrique: tener el Telegram del cliente registrado en Odoo para mandarle
mensajes **sin que él inicie** (al revés de WhatsApp). El candado de Telegram: el cliente
debe dar `/start` UNA vez (eso = su consentimiento); después le mandamos ilimitado.

### Bot creado
- **@SentinelaAvisos_bot** (nombre visible **SentiBot**, id `8688475458`). 3er bot, separado
  de los internos Sentinela/SentinelaNet. Sin webhook (validado con getMe/getWebhookInfo).
- Token + usuario sembrados **solo en V18** (`ir.config_parameter`
  `sentinela_monitoring.telegram_client_bot_token` / `_username`), **NO en el repo**.

### Rutina de vinculación (monitoring v18.0.1.30.0 → .31.0)
- `res.partner`: `telegram_link_token` (token auto en `create` + backfill de ~3,102
  existentes), `telegram_link_url`, `telegram_opt_in_date` (consentimiento).
- Botón **"Generar liga de vinculación"** (pestaña Notificaciones) → `t.me/<bot>?start=<token>`.
- **Cron "Vinculación Telegram" (cada 1 min, getUpdates):** casa `/start <token>` con el
  partner y escribe `telegram_chat_id` solo; offset en `ir.config_parameter`. El bot NO debe
  tener webhook (getUpdates → 409). Solo el proceso V18 corre el cron (staging sin crones).
- `_get_telegram_token()` repuntado al Bot Clientes (fallback al histórico) → el bot que
  captura el chat_id es el mismo que envía.
- **Matiz per-bot (corregido en vivo):** el número `chat_id` = user id de Telegram (igual
  entre bots), pero el permiso de envío es por-bot (requiere `/start` a ese bot).
- **Probado REAL** en partner 20826 (Enrique, chat_id 7965190381): vinculación + envío
  end-to-end OK (mensaje de prueba recibido desde el bot nuevo).

### Link de rastreo de técnico/patrulla — YA funcionaba por el bot nuevo
- `fsm_order.action_start()` → `partner.notify()` → `send_telegram_message` →
  `_get_telegram_token()` (repuntado). Sin código extra.
- **Probado REAL:** orden OS-00034 a 20826 → llegó "Técnico en camino" + link
  `/SentiCar/rastreo/<token>` por Telegram (canal reportado: telegram). Orden de prueba
  **borrada** después.

### Captación de vinculaciones — QR PASIVO en factura + portal (cfdi v18.0.1.1.16 + monitoring .31.0)
- **Decisión:** NO blast masivo por WhatsApp (EvoApi no oficial → riesgo de baneo de la
  línea de SOPORTE). En su lugar, QR pasivo embebido.
- `_telegram_qr_for_report()` (QR PNG base64 vía `qrcode`, ya instalado en el contenedor):
  devuelve False si el cliente YA está vinculado → no lo molesta.
- **QR "Únete a Sentinela en Telegram"** embebido en: (1) PDF factura/remisión
  (`sentinela_cfdi_prodigia/report_invoice.xml`, guardado `'telegram_link_token' in _fields`);
  (2) tarjeta en `portal.portal_my_home`.
- **Verificado:** render HTML de `INV/2026/00136` (cliente no vinculado) trae el bloque + QR,
  **sin romper la impresión**; partner vinculado NO ve el QR.

### Deploy / releases
- monitoring: `0c58332` (v.30.0) + `cb3c357` (v.31.0), tags pusheados.
- cfdi_prodigia: `cb3c357` (v18.0.1.1.16), tag pusheado.
- rsync → `-u` STAGING (limpio) → backfill tokens → `-u` V18 + restart → versiones
  confirmadas en DB (`18.0.1.31.0` / `18.0.1.1.16`). Cron activo corriendo limpio (0.5s).

## Pendientes para la próxima sesión
1. **Syscom quick-wins futuros (no hechos):** galería de imágenes múltiples; cron de
   facturas de compra automático + match con OC; precios por volumen para compras; mapear
   `clave_unidad_sat` → uom real de Odoo (hoy solo se guarda informativo).
2. Productos existentes se **enriquecen poco a poco** conforme el cron nocturno los recorra
   (o al re-importar por wizard); los nuevos ya entran completos.
3. (Opcional) Anonimizar nombres de clientes en la Guía de Cobranza — Enrique dijo que NO
   hace falta.
4. (Opcional) Saneamiento automático de `default_code` con espacios en el módulo Syscom,
   por si la re-importación vuelve a meter espacios.
5. **Telegram caso 2 — QR del técnico:** botón "Mostrar QR de vinculación" en la orden FSM /
   el contacto, para que el técnico se lo enseñe al cliente al terminar la instalación.
6. **Telegram caso 3 — Prospectos:** liga/QR genérico → el cron crea un partner
   "Prospecto Telegram" (con dedup por teléfono) etiquetado para mercadeo, a revisión.
7. **Telegram — re-vincular** clientes ya existentes bajo el bot nuevo (los chat_id viejos
   del bot de netwatch quedan "dormidos" hasta que cada quien dé `/start` al bot nuevo).
8. **Telegram alarmas — throttle/dedup por cuenta** (1 aviso cada N min) antes de conectar la
   activación de alarmas al bot, apoyado en la detección de "posible falsa alarma" que ya existe.
9. (Opcional) Goteo de invitación por WhatsApp solo a clientes con historial previo
   (personalizado, tandas chicas) — NO blast masivo.
