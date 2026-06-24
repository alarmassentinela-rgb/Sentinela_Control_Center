# Resumen de sesión — 24 de junio de 2026

Sesión centrada en **SentiCar (Traccar)**: cierre del correo de recuperación de
contraseña, manual de usuario para clientes (ES+EN), y migración de 6 GPS de
Smake a SentiCar.

---

## 1. SentiCar — Recuperación de contraseña ("Olvidé mi contraseña")

### 1.1 Habilitación (ya venía de antes en el día)
- SMTP en `~/traccar/traccar.xml` (relay `mail.sentinela.com.mx:465`, From
  `gps@senticar.com`, auth `contacto@sentinela.com.mx`). `emailEnabled:true` → el
  enlace "Reiniciar contraseña" aparece en el login.
- SPF + DMARC publicados en Cloudflare para `senticar.com`; sin MX (no recibe).

### 1.2 Fix del enlace `172.20.0.2:8082` (BUG real resuelto)
- **Síntoma:** el correo llegaba con diseño OK pero el botón/liga apuntaban a la IP
  interna del contenedor Docker → inalcanzable.
- **Causa:** el template `passwordReset.vm` usa `$webUrl`, que Traccar saca de la
  config **`web.url`**; no estaba definida → la deducía de la conexión entrante.
- **Fix:** se agregó `<entry key='web.url'>https://radar.senticar.com</entry>` a
  `traccar.xml` + restart. Verificado: link sale `https://radar.senticar.com/reset-password?...`.
  Backup `~/traccar/traccar.xml.bak_weburl_24jun`.

### 1.3 Decisión no-reply
- Traccar **no soporta Reply-To** (verificado en su clase `SmtpMailManager`: solo
  `from`/`fromName`). `mail.sentinela.com.mx` es hosting externo (170.10.161.117).
- **Decisión de Enrique:** dejar `gps@senticar.com` como **no-reply** + leyenda al pie
  de `passwordReset.vm` (ES y EN): "Este es un correo automático, por favor no
  respondas a este mensaje." Backups `*.bak_noreply_24jun`.
- **Quién lee `gps@senticar.com`:** nadie — sin MX, las respuestas rebotan.

---

## 2. SentiCar — Rol de usuarios cliente (confirmación)
- Confirmado contra código + `/api/users` de prod: los usuarios que provisionamos son
  **manager acotado a su propia cuenta** (`userLimit=-1`, `limitCommands=True`,
  **`administrator=False`**), NUNCA super-admin global. Ven solo su subárbol
  (su grupo + subgrupos + sub-usuarios que creen); no ven cuentas hermanas.
- Solo son admin global: egarza (id1), hijo (id5), cuenta servicio Odoo (id2).

---

## 3. SentiCar — Manual del Administrador de Cuenta (ES + EN)
- Manual completo para clientes tipo KAWAC/Parker (rol admin de su cuenta, no super-admin):
  mapa, equipos, seguir, compartir link temporal, reportes, geocercas, crear sus
  usuarios, editar equipo, cambiar/recuperar contraseña, límites del rol, soporte.
- **Capturas reales** de `radar.senticar.com` tomadas con Playwright (cuenta flota
  `contacto@sentinela.com.mx`); EN con `locale=en-US`.
- Generadores versionados: `gen_manual_admin_cuenta_senticar.py` (ES) y
  `gen_manual_admin_account_senticar_en.py` (EN).
- PDFs: `MANUAL_ADMIN_CUENTA_SENTICAR.pdf` + `SENTICAR_ACCOUNT_ADMIN_MANUAL_EN.pdf`.
- **Commiteado + pusheado** (commit `f198df9`). Ambos enviados a Telegram de Enrique.
- Trampa documentada: la pantalla "Compartir"/"Account" de Traccar crashea por
  navegación directa (necesita estado de React Router); capturar vía clic in-app o
  desde `/settings/preferences` → menú lateral.

---

## 4. Migración Smake → SentiCar (6 GPS, todos N01/N01H = GT06, puerto 5023)
Receta confirmada end-to-end (no requiere reconfigurar APN: las SIM ya traían datos
de Smake). Pasos por sub: plataforma=senticar + cargar equipos → crear cuenta cliente
+ `action_provision_senticar` (registra IMEI en Traccar, offline) → `action_activate`
(cobro normal) → SMS cutover por equipo: **`SERVER,1,gps.senticar.com,5023,0#`**
(template #2 N01K/GT06; ⚠️ escribir `gps_sms_command` explícito antes de
`action_send_sms`, el onchange no persiste entre sesiones de shell).

### 4.1 SUB-0400 — MANGUERAS Y CONEXIONES DEL BRAVO ("Parker", partner 21675)
- Archivo origen: `Downloads/mangueras.xlsx`. Activa, cobro 2026-07-01.
- Usuario SentiCar: `administracionbravo@parkermatamoros.com.mx` / `Sc2a57c61706`.
- 3 equipos, **los 3 con fix válido** en <75s:
  - Avanza (IMEI 869671070142979, placas WX-1673-B) → 26.0382,-98.3616
  - HILUX (865167041843716) → 26.0529,-98.3659
  - HILUX #2 (865167041843880) → 25.8706,-97.5182

### 4.2 SUB-0399 — CILINDROS Y MANGUERAS DE REYNOSA (Fam. Ortiz Flores, partner 20526)
- Archivo origen: `Downloads/Cilindros.xlsx`. Activa, cobro 2026-07-01.
- Usuario SentiCar: `vflores@parkermatamoros.com.mx` / `Sc8d0904a693`.
- 3 equipos, los 3 online por GT06 (cutover hecho):
  - Tacoma (869671077938387) → **fix válido** 25.6606,-100.2578 (Monterrey)
  - TAOS Blanca (869671077931747) → online, sin fix aún (estacionado)
  - Mercedez (869671077931523) → online, sin fix aún (estaba 13 h detenido)

> Nota técnica: `start_date` de las subs quedó en 2020-02-01 (default raro del plan);
> NO afecta el cobro, que lo rige `next_billing_date=2026-07-01`. Cosmético.

---

## Pendientes para mañana
1. **Mercedez (SUB-0399, device 14 / sid 14):** reporta `0,0`/`valid=False` → aparece
   "en el mar" (isla nula) por falta de fix GPS (cold start estacionado bajo techo).
   El cutover SÍ ocurrió (online por GT06). Verificar que fije al moverse/cielo abierto.
2. **TAOS Blanca (SUB-0399, device 13):** igual, confirmar fix cuando se mueva.
3. **Filtro coordenadas-cero en Traccar (opcional, pendiente de decisión):** activar
   `filter.zeroCoordinates` para que equipos sin fix no aparezcan en `0,0` (el mar).
   Es global + requiere restart (~5s). Enrique no decidió aún.
4. **`start_date` 2020-02-01** en SUB-0399/0400: corregir a fecha real si se quiere
   (cosmético, no afecta cobro).
5. Opcional: validar score de spam real (mail-tester) del correo de recuperación.
