# Procedimiento — Stripe CLI para webhooks en STAGING (Sprint 2 / Cobranza)

**Fecha:** 2026-06-30 · **Contexto:** Etapa 3 del `PLAN_RC1_SPRINT2_COBRANZA.md` (pendiente de autorización).
**Decisión de Enrique:** usar **Stripe CLI** para recibir webhooks en STAGING. **NO se expone públicamente el Gateway de STAGING.**
**Estado:** documento de procedimiento. **No se ha instalado, autenticado ni ejecutado nada todavía.**

> El listener de Stripe CLI abre una conexión **saliente** a Stripe y **reenvía** los eventos al Gateway por `localhost`. No abre ningún puerto entrante ni superficie pública. Es exactamente lo que queremos para STAGING.

---

## 0. Datos reales del entorno (verificados en el Pre-Flight)
| Dato | Valor |
|---|---|
| Host donde corre el CLI | **server `192.168.3.2`** (Ubuntu 24.04.4, **x86_64**); tiene salida a `api.stripe.com` ✅ |
| Gateway STAGING | contenedor `coc-gw-staging`, `--network host`, **uvicorn :8401** |
| **Endpoint de webhook** | **`POST /v1/payments/webhook`** (cabecera `stripe-signature`, firma verificada) |
| **Forward target** (CLI en el server) | **`http://127.0.0.1:8401/v1/payments/webhook`** |
| Eventos que traduce el adaptador | `payment_intent.succeeded`, `payment_intent.payment_failed`, `payment_intent.processing`, `payment_intent.canceled` |
| Variables del Gateway (prefijo `COC_`) | `COC_STRIPE_SECRET_KEY`, `COC_STRIPE_WEBHOOK_SECRET`, `COC_STRIPE_PUBLISHABLE_KEY` |
| Variable de la SPA (build-time) | `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` |

---

## 1. Instalación de Stripe CLI (en el server)
Stripe CLI **no está instalado** (verificado). Dos opciones; **recomiendo la B** (sin tocar repos del sistema).

### Opción A — repositorio APT oficial (requiere sudo)
```bash
curl -s https://packages.stripe.dev/api/security/keypair/stripe-cli-gpg/public \
  | gpg --dearmor | sudo tee /usr/share/keyrings/stripe.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/stripe.gpg] https://packages.stripe.dev/stripe-cli-debian-local stable main" \
  | sudo tee /etc/apt/sources.list.d/stripe.list
sudo apt update && sudo apt install -y stripe
```

### Opción B — binario al `~/bin` del usuario (sin root) ✅ recomendada
```bash
mkdir -p ~/bin
# Sustituir <VER> por la última versión estable (https://github.com/stripe/stripe-cli/releases)
curl -L "https://github.com/stripe/stripe-cli/releases/download/v<VER>/stripe_<VER>_linux_x86_64.tar.gz" \
  -o /tmp/stripe.tar.gz
tar -xzf /tmp/stripe.tar.gz -C ~/bin stripe
export PATH="$HOME/bin:$PATH"   # añadir a ~/.bashrc para que persista
```

### Verificar instalación
```bash
stripe version
```

---

## 2. Autenticación con Stripe (modo test)
El server es *headless*. Dos caminos:

### Camino 1 — `stripe login` (emparejamiento por navegador) — preferido
```bash
stripe login
```
Imprime una URL + un *pairing code*. **Abre la URL en tu navegador** (tu laptop), confirma el código y autoriza la cuenta **en modo test**. Las credenciales quedan en `~/.config/stripe/config.toml`. A partir de aquí, los comandos usan esa sesión sin pasar la clave.

### Camino 2 — sin login, clave por comando (totalmente headless)
No ejecutar `stripe login`; pasar la clave **test** en cada comando con `--api-key` (o `export STRIPE_API_KEY=sk_test_...`). Útil si no quieres almacenar la sesión:
```bash
export STRIPE_API_KEY="sk_test_..."   # SOLO en la shell del listener; nunca commitear
```

> En ambos casos: **usar exclusivamente claves `…_test_…`**. Nunca `sk_live`/`pk_live` en STAGING.

---

## 3. Levantar `stripe listen` + forward al Gateway
Comando base (en la shell del server, dentro de `tmux`/`screen` para que sobreviva a la sesión SSH):
```bash
stripe listen \
  --forward-to http://127.0.0.1:8401/v1/payments/webhook \
  --events payment_intent.succeeded,payment_intent.payment_failed,payment_intent.processing,payment_intent.canceled
```
(si usas el Camino 2, añade `--api-key "$STRIPE_API_KEY"`).

Al arrancar imprime:
```
> Ready! You are using Stripe API Version [...]. Your webhook signing secret is whsec_xxxxxxxx (^C to quit)
```

**Ese `whsec_xxxxxxxx` es el secreto de firma del listener** → es el valor que va en `COC_STRIPE_WEBHOOK_SECRET` del Gateway.

> El `whsec` del CLI es **estable por cuenta** (no cambia entre sesiones de `listen`). Puedes obtenerlo sin arrancar el forward con:
> ```bash
> stripe listen --print-secret
> ```

### Ejecución persistente (recomendado para la ventana de UAT)
```bash
tmux new -s stripe-staging
# dentro de tmux:
stripe listen --forward-to http://127.0.0.1:8401/v1/payments/webhook \
  --events payment_intent.succeeded,payment_intent.payment_failed,payment_intent.processing,payment_intent.canceled
# Ctrl-b d  → desadjuntar (el listener sigue vivo)
```

---

## 4. Variables de entorno necesarias (para la Etapa 3 — NO aplicar aún)
> Estas se inyectarán al **recrear** los contenedores durante la Etapa 3 (el `coc-gw-staging` corre con `--network host` vía `docker run --env-file`; la SPA hornea `NEXT_PUBLIC_*` en build). **No se aplican en este paso.**

**Gateway (`coc_gw_staging.env`):**
```ini
COC_STRIPE_SECRET_KEY=sk_test_...        # provista por Enrique
COC_STRIPE_PUBLISHABLE_KEY=pk_test_...   # provista por Enrique (informativa en el gateway)
COC_STRIPE_WEBHOOK_SECRET=whsec_...      # la que imprime `stripe listen` / `--print-secret`
```
**SPA (build de STAGING):**
```ini
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...   # la usa el front para crear el PaymentIntent
```

**Orden de obtención:** primero `pk_test`/`sk_test` (Enrique) → luego `whsec` (lo genera el listener en el paso 3) → entonces se completan las 4 variables.

---

## 5. Verificación de recepción de eventos
Con el listener arriba y el Gateway STAGING ya configurado con el `whsec` (Etapa 3):

1. **Disparar un evento de prueba** (otra shell del server):
   ```bash
   stripe trigger payment_intent.succeeded
   ```
2. **En la ventana del listener** debe verse el evento y la respuesta del forward:
   ```
   payment_intent.succeeded -> POST http://127.0.0.1:8401/v1/payments/webhook [200]
   ```
   Un `[200]` confirma firma válida + procesamiento. Un `[400] invalid_signature` = el `whsec` del Gateway no coincide con el del listener.
3. **Logs del Gateway** (confirmación independiente):
   ```bash
   docker logs --tail 50 coc-gw-staging
   ```
4. **Flujo real end-to-end** (Etapa 4): pagar desde la SPA con tarjeta de prueba `4242 4242 4242 4242` (fecha futura/CVC cualquiera) → se crea el PaymentIntent → Stripe emite `payment_intent.succeeded` → el listener lo reenvía → `pago.confirmado` → aplicación → `factura.pagada`.
   - Rechazo: tarjeta `4000 0000 0000 0002` → `payment_intent.payment_failed` → `pago.rechazado` (sin aplicar).

---

## 6. Detener el listener
- **En primer plano:** `Ctrl-C` en la ventana del `stripe listen`.
- **En tmux:** `tmux attach -t stripe-staging` → `Ctrl-C` → `exit` (o `tmux kill-session -t stripe-staging`).
- **Por proceso (último recurso):**
  ```bash
  pkill -f "stripe listen"
  ```
- **Limpieza de credenciales** (si se usó `stripe login` y se quiere cerrar sesión):
  ```bash
  stripe logout
  ```
- Al cerrar la UAT, además: quitar las claves Stripe de la shell/entorno y NO dejarlas en archivos versionados.

---

## 7. Notas de seguridad
- **Solo claves `test`.** Verificar que `sk_test`/`pk_test`/`whsec` provienen del entorno *Test* del dashboard de Stripe (toggle "Test mode" ON).
- **Nunca commitear** ninguna clave. `coc_gw_staging.env` está fuera del repo (en `~/`); el `.gitignore` del repo excluye `.env`.
- El listener no requiere abrir puertos entrantes → **no se modifica ufw ni se expone el Gateway**. La regla `8401 ALLOW 192.168.3.0/24` (LAN, UAT) se mantiene como está.
- El `whsec` del CLI es distinto del `whsec` de un endpoint del dashboard; si más adelante (Producción) se registra el webhook público real, ese tendrá **su propio** `whsec`.

---

## 8. Checklist de readiness para re-correr el Pre-Flight
- [ ] Stripe CLI instalado (`stripe version` responde).
- [ ] Autenticado en modo test (`stripe login`) **o** `sk_test` disponible para `--api-key`.
- [ ] `sk_test` y `pk_test` entregadas por Enrique.
- [ ] `stripe listen` arranca y entrega un `whsec_…`.
- [ ] Las 4 variables (`COC_STRIPE_SECRET_KEY`, `COC_STRIPE_PUBLISHABLE_KEY`, `COC_STRIPE_WEBHOOK_SECRET`, `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`) listas para inyectarse en la Etapa 3.
- [ ] `stripe trigger payment_intent.succeeded` → listener `[200]` contra el Gateway (se valida ya en Etapa 3/4, una vez configurado el `whsec`).

> Cuando estos puntos estén resueltos, **re-ejecutamos el Pre-Flight completo**; solo con todo en verde se solicitará la autorización de la Etapa 3.
