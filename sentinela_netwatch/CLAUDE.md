# sentinela_netwatch

Vigilante de la **red WISP** (Fase 0): programa Python **independiente del router** que hace ping a antenas/sectoriales/enlaces (`10.10.10.x`), lee solo-lectura las WAN del Balanceador, sirve un dashboard NOC y alerta por Telegram qué sector/radio base se cayó. **NO es un módulo Odoo** (no tiene `__manifest__.py` ni `models/`): es una app standalone Flask+gunicorn que corre en Docker. **NO confundir con `sentinela_monitoring`** (eso son alarmas/Securithor); esto es infraestructura de red WISP.

> Este archivo se auto-carga al trabajar en el módulo. Documenta el **cómo es el código** (arquitectura, trampas). El **estado/decisiones** del proyecto vive en la memoria (`MEMORY.md`), no aquí. Si cambias algo estructural, actualiza este archivo.

- **No versionado por manifest:** no hay `__manifest__.py` ni `version`. Es código suelto desplegado por rsync + `docker compose restart`.
- **Stack:** Python 3.12 · Flask + gunicorn (1 worker, 8 threads) · SQLite (eventos) · TimescaleDB/PG16 (consumo Fase 2).
- **Deploy:** NO usa las skills `release-modulo`/`deploy-modulo` (esas son para addons Odoo `sentinela_*`). Aquí: editar local → `rsync` a `192.168.3.2` → `docker compose restart` (el volumen monta `.:/app`, por eso reinicio basta y casi nunca se reconstruye imagen). Sin rsync, el contenedor corre código viejo igual que con los addons. **DB consumo:** TimescaleDB en contenedor `sentinela_timescaledb`.

## Dependencias (requirements.txt)
| Paquete | Para qué |
|---|---|
| `flask` | servidor del dashboard (`/` y `/api/status`) en modo dev |
| `gunicorn` | servidor WSGI en producción (`vigilante:app`) |
| `requests` | enviar mensajes a Telegram (`api.telegram.org`) |
| `routeros_api` | leer netwatch del Balanceador y contadores PPPoE del CCRsentinela (API MikroTik) |
| `psycopg2-binary` | escribir consumo en TimescaleDB (Fase 2) |

`xmlrpc.client` (stdlib) se usa para espejar clientes desde Odoo. `iputils-ping` se instala en el Dockerfile (el ping usa `subprocess` al binario del sistema, no librería Python).

## Archivos (no hay models/)
| Archivo | Rol |
|---|---|
| `vigilante.py` | Núcleo: colector de ping (hilo loop) + Telegram + servidor Flask del dashboard. Expone `app` (WSGI para gunicorn). |
| `collector_traffic.py` | Fase 2: hilo aparte que lee contadores PPPoE del CCRsentinela, calcula deltas y los guarda en TimescaleDB. Lo arranca `vigilante.iniciar_collector()`. |
| `build_inventory.py` | Regenera `inventory.json` desde UISP API + dispositivos ciegos (`BLIND`) identificados a mano. Se corre manual, no en el loop. |
| `inventory.json` | Qué vigilar: `ip -> {name, tipo, radio_base, clientes, backhaul, ...}` (53 dispositivos: 29 sectorial, 12 enlace, 6 switch, 4 desconocido, 1 estacion, 1 otro). |
| `dashboard.html` | Pantalla NOC; se lee a memoria al importar (`DASHBOARD_HTML`) y se sirve en `/`. |
| `status.json` | Snapshot del estado vivo que `publicar()` reescribe cada ronda (lo consume el dashboard vía `/api/status`). |
| `netwatch.db` | SQLite con tabla `eventos` (histórico caídas/recuperaciones). Se crea solo. |
| `docker-compose.yml` / `Dockerfile` | 2 servicios: `netwatch` (network_mode host) + `timescaledb`. |

## Campos de estado clave
Cada dispositivo en `DEVICES[ip]["estado"]` (Selection informal, string):
| Estado | Significado |
|---|---|
| `desconocido` | recién cargado, antes de la primera ronda |
| `up` | responde a ping |
| `down` | dejó de responder ≥ `FAIL_THRESHOLD` rondas (estaba `up`) → genera alerta |
| `inactivo` | NO respondió en el baseline inicial (decomisionado) → `monitored=False`, **no alerta** hasta revivir |

`tipo` de dispositivo (en inventory.json) gobierna alertas y dashboard:
| tipo | Efecto |
|---|---|
| `sectorial`, `enlace`, `switch` | en `ALERT_TIPOS` → **sí** avisan a Telegram |
| `estacion` | CPE de cliente: **no** se muestra en el dashboard ni alerta |
| `otro` / `desconocido` | se vigilan por IP pero **no** alertan a Telegram |

WAN del Balanceador: `WANS[comment]` solo guarda netwatch cuyo comment empieza con `WAN`; `WANS["_error"]` si la lectura falló.

## "Crones" — NO hay ir_cron; son loops `time.sleep` en hilos daemon
No existe `data/*.xml` ni `ir.cron`. La cadencia vive en bucles Python:
| Loop (archivo) | Método | Cadencia | Qué hace |
|---|---|---|---|
| `vigilante.loop()` | `ronda(primera=False)` | `INTERVAL_S` = 20 s | Ping paralelo (30 workers) a todo el inventario, debounce, alertas, `publicar()` |
| `vigilante.loop()` | `leer_wans()` | cada 3 ciclos (~1 min) | Lee `/tool/netwatch` del Balanceador (`192.168.10.254`) |
| `collector_traffic.loop()` | `collect_once()` | `INTERVAL_S` = 600 s (10 min) | Lee `<pppoe-ctaXXXX>` del CCRsentinela (`192.168.10.50`), delta → tabla `traffic` |
| `collector_traffic.loop()` | `refresh_clients()` | cada 6 ciclos (~1 h) | Espeja `cta → partner/plan` desde Odoo (`sentinela.subscription`, XML-RPC) a tabla `clients` |

Umbrales debounce: `FAIL_THRESHOLD=3` (≈1 min para declarar down), `OK_THRESHOLD=2` para recuperar, `PING_TIMEOUT_S=1`.

## Flujos importantes
- **Baseline:** la primera `ronda(primera=True)` fija estado inicial **sin alertar**; lo que no responde entra `inactivo`/no-monitoreado.
- **Anti-flapping (debounce):** down solo tras `FAIL_THRESHOLD` rondas seguidas sin responder; up tras `OK_THRESHOLD`. El ping manda 3 paquetes y basta que 1 responda (tolera ICMP intermitente).
- **Supresión topológica:** si cae un `enlace` backhaul de una zona, se manda **un** aviso "RADIO BASE X AISLADA" con clientes afectados, en vez de spamear cada sectorial detrás (mapa `BACKHAUL_ZONA`). Si un sectorial cae pero su enlace ya está down, se suprime.
- **Dashboard NOC :8090** — `GET /` sirve `dashboard.html`; `GET /api/status` devuelve el snapshot (`publicar()`): WANs, dispositivos agrupados por `zona()` (nombres limpios: Brisas, Quinta Real, Parker, Las Rusias, Saucito, Cd. Industrial, Monclova, Central…), y resumen up/down/inactivos.
- **Alertas Telegram** por sector/radio base con 3 plantillas: "RADIO BASE X AISLADA" (backhaul), "Switch de torre caído", "Sectorial caído ~N clientes", y "🟢 Recuperado". Mismo bot que las alertas WAN (`TG_TOKEN`/`TG_CHAT` hardcodeados arriba de `vigilante.py`); `TG_ON=False` = modo prueba.
- **Fase 2 consumo:** PPPoE expone `<pppoe-ctaXXXX>` con `tx-byte`=DESCARGA y `rx-byte`=SUBIDA del cliente (acumulados). `collect_once` calcula delta vs `last_counter`, maneja el reset al reconectar, e inserta en hypertable `traffic` (retención 90 días + agregados continuos `traffic_daily`/`traffic_monthly`).

## Trampas conocidas
- **NO es Odoo.** No le apliques `release-modulo`/`deploy-modulo`; no tiene manifest ni versión. Deploy = rsync + `docker compose restart`.
- **Credenciales hardcodeadas** en el código (no en env): Telegram, API MikroTik (`gemini_api`/`gemini_api2113`), TimescaleDB (`NetwatchTS2026!`), Odoo (`api_user`/`SentinelaBot2026!`), token UISP en `build_inventory.py`. Cuidado al compartir/commitear.
- **Desfase de puerto TimescaleDB:** compose publica `5435:5432`, pero comentarios (compose y README) dicen `5433`. El código (`collector_traffic.TS_PORT`) usa **`5435`**, que es lo correcto. Ignora los comentarios viejos.
- **`network_mode: host` obligatorio** para alcanzar `10.10.10.x`, el Balanceador y conectar a TimescaleDB por `127.0.0.1:5435`.
- **Arranque del colector al importar:** `iniciar_collector()` corre al importar `vigilante` (gunicorn lo importa) salvo con `--once`. Es idempotente (flag + lock) para no duplicar hilos. Con `gunicorn -w 1` hay un solo colector; **subir workers duplicaría pings y deltas**.
- **`ODOO_DB="Sentinela_V18"` y `ODOO_URL=:8070`** están fijos en `collector_traffic.py` (apunta a prod, no a STAGING).
- **Semántica tx/rx invertida** respecto a la intuición: en PPPoE server, `tx-byte`=bajada del cliente, `rx-byte`=subida. Documentado en el código; no lo "corrijas".
- **`build_inventory.py` no se corre solo** — regenera `inventory.json` desde UISP; hay ~10 dispositivos ciegos (`.40 .41 .240 .241` sin identificar, switches `.59-.65`) puestos a mano en `BLIND`.
- **Pings con `subprocess`** al binario `ping` del SO (por eso el Dockerfile instala `iputils-ping`); no es ICMP en Python.

## Modos de ejecución
- `python3 vigilante.py --once` — una ronda baseline, imprime resumen por zona, **sin web ni alertas ni colector** (diagnóstico).
- `python3 vigilante.py` — Flask dev en `0.0.0.0:8090` + colector.
- Producción: `gunicorn -w 1 --threads 8 -b 0.0.0.0:8090 --timeout 120 vigilante:app` (Dockerfile CMD).

## No aplica
No hay `wizard/`, `controllers/` Odoo (las rutas son Flask), `security/`, `report/` ni `tests/`. La documentación de diseño de Fase 2 está en `DISEÑO_FASE2_CONSUMO.md` y la operativa en `README.md`.
