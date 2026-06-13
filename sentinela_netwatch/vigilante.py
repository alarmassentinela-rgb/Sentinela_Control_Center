#!/usr/bin/env python3
"""
SENTINELA NETWATCH — Vigilante de red WISP (FASE 0)
====================================================
Programa INDEPENDIENTE que corre FUERA del router. Cada ciclo:
  1. Hace ping directo a todas las antenas/sectoriales/enlaces (inventory.json).
  2. Lee (solo lectura) el estado de las WAN 1/2/3 desde el Balanceador.
  3. Detecta caidas con anti-flapping (debounce) y supresion topologica.
  4. Avisa a Telegram el sector/radio base afectado + clientes.
  5. Guarda historico en SQLite y publica estado vivo para el dashboard.

Dashboard web en http://<host>:8090/  (pensado para monitor permanente de NOC).
NO modifica nada en el router. Solo ping + lectura.
"""
import os, json, time, sqlite3, subprocess, threading, datetime
from concurrent.futures import ThreadPoolExecutor

# ───────────────────────── CONFIG ─────────────────────────
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
INVENTORY  = os.path.join(BASE_DIR, "inventory.json")
DB_PATH    = os.path.join(BASE_DIR, "netwatch.db")
STATUS_OUT = os.path.join(BASE_DIR, "status.json")

INTERVAL_S      = 20      # segundos entre rondas de ping
FAIL_THRESHOLD  = 3       # rondas seguidas sin responder = CAIDO (anti-flapping)
OK_THRESHOLD    = 2       # rondas seguidas OK = RECUPERADO
PING_TIMEOUT_S  = 1       # timeout por ping
WORKERS         = 30      # pings en paralelo
WEB_PORT        = 8090

# Telegram (mismo bot que ya usas para alertas WAN)
TG_TOKEN = "8297148416:AAGC1gf2tElL2xxe83av0b9uXuln0usIrZA"
TG_CHAT  = "7965190381"
TG_ON    = True            # False = modo prueba (no envia Telegram)

# Balanceador (solo LECTURA del netwatch de WANs)
BAL_HOST = "192.168.10.254"
BAL_USER = "gemini_api"
BAL_PASS = "gemini_api2113"
WAN_READ = True           # poner False si no quieres leer las WAN

# ─── Enlace FFW (2x Ubiquiti Wave 60GHz) — monitoreo por API HTTP (NO ping) ───
# Se administran por API (login -> x-auth-token), no por SSH airOS. Vigila: enlace
# activo, señal, y el puerto ETHERNET (el cuello de botella conocido: la .4 negocia
# a 100M con drops -> tope ~83M aunque el radio da 1.6 Gbps). Alerta por CAMBIO.
WAVES_FFW = {
    "10.99.99.3": "FFW · lado Oficina",
    "10.99.99.4": "FFW · lado Maquiladora",
}
WAVE_USER         = "sentinela"
WAVE_PASS         = "SentinelaW1sp#"
WAVE_SIGNAL_WARN  = -75       # peor (más negativo) que esto = señal degradada
WAVE_SIGNAL_OK    = -72       # mejor que esto = recuperada (histéresis)
WAVE_CHECK_EVERY  = 15        # cada N ciclos del loop (15·20s ≈ 5 min)
WAVE_READ         = True

# ───────────────── ZONA / RADIO BASE (nombres limpios) ─────────────────
def zona(name, uisp_site):
    n = (name or "").lower()
    if "brisas" in n:                              return "Brisas"
    if "qr" in n or "quinta" in n:                 return "Quinta Real"
    if "pk" in n or "parker" in n:                 return "Parker"
    if "rusias" in n:                              return "Las Rusias"
    if "saucito" in n:                             return "Saucito"
    if "cdind" in n or "cd. ind" in n:             return "Cd. Industrial"
    if "mva" in n or "monclova" in n:              return "Monclova"
    if n.startswith("sec") or n.startswith("base sec") or "oficina" in n:
        return "Central"
    if uisp_site and uisp_site not in ("?", "Caballero Hilario, MIguel Angel"):
        return uisp_site.replace("Radio Base ", "")
    return "Otros / sin clasificar"

# Enlaces backhaul -> zona que aislan si caen (para supresion de spam)
BACKHAUL_ZONA = {
    "10.10.10.230": "Parker",      "10.10.10.229": "Parker",
    "10.10.10.50":  "Brisas",      "10.10.10.51":  "Brisas",  "10.10.10.250": "Brisas",
    "10.10.10.202": "Quinta Real", "10.10.10.203": "Quinta Real",
    "10.10.10.210": "Las Rusias",  "10.10.10.211": "Las Rusias",
    "10.10.10.252": "Saucito",     "10.10.10.227": "Saucito",
}

# ───────────────────────── ESTADO ─────────────────────────
LOCK = threading.Lock()
DEVICES = {}     # ip -> dict (datos + estado vivo)
WANS = {}        # nombre -> {"label","status"}
WAVES = {}       # ip -> snapshot vivo del enlace FFW (para dashboard)
WAVE_ALERTSTATE = {}  # ip -> {reachable,link,eth_ok,signal_ok} (para detectar cambios)
WAVES_STARTED = False
STARTED_AT = None

def now():
    return datetime.datetime.now()
def ts():
    return now().strftime("%Y-%m-%d %H:%M:%S")

# ───────────────────────── DB ─────────────────────────
def db():
    c = sqlite3.connect(DB_PATH)
    c.execute("""CREATE TABLE IF NOT EXISTS eventos(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT, ip TEXT, nombre TEXT, zona TEXT, tipo TEXT,
        de TEXT, a TEXT, clientes INTEGER)""")
    return c

def log_evento(d, old, new):
    c = db()
    c.execute("INSERT INTO eventos(fecha,ip,nombre,zona,tipo,de,a,clientes) VALUES(?,?,?,?,?,?,?,?)",
              (ts(), d["ip"], d["name"], d["zona"], d["tipo"], old, new, d.get("clientes", 0)))
    c.commit(); c.close()

# ───────────────────────── TELEGRAM ─────────────────────────
def tg(msg):
    if not TG_ON:
        print("  [TG-OFF]", msg.replace("\n", " | ")); return
    try:
        import requests
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      data={"chat_id": TG_CHAT, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception as e:
        print("  [TG-ERR]", e)

# ───────────────────────── PING ─────────────────────────
def ping(ip):
    # 3 paquetes: basta que UNO responda (tolera perdida intermitente, ej. appliances que limitan ICMP)
    try:
        r = subprocess.run(["ping", "-c", "3", "-i", "0.3", "-W", str(PING_TIMEOUT_S), ip],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return r.returncode == 0
    except Exception:
        return False

# ───────────────────────── WAN (lectura Balanceador) ─────────────────────────
def leer_wans():
    if not WAN_READ:
        return
    try:
        import routeros_api
        pool = routeros_api.RouterOsApiPool(BAL_HOST, username=BAL_USER, password=BAL_PASS,
                                            plaintext_login=True)
        api = pool.get_api()
        nw = api.get_resource("/tool/netwatch").get()
        with LOCK:
            WANS.clear()
            for r in nw:
                c = r.get("comment", "") or ""
                if c.upper().startswith("WAN"):
                    WANS[c] = {"label": c.replace("-", " "), "status": r.get("status", "?")}
        pool.disconnect()
    except Exception as e:
        with LOCK:
            WANS["_error"] = {"label": "WAN (sin lectura)", "status": str(type(e).__name__)}

# ───────────────────── ENLACE FFW (Wave 60GHz por API) ─────────────────────
def _wave_read(ip):
    """Login a la Wave y devuelve métricas clave del enlace, o {'reachable':False}."""
    import requests
    try:
        login = requests.post(f"https://{ip}/api/v1.0/user/login",
                              json={"username": WAVE_USER, "password": WAVE_PASS},
                              verify=False, timeout=8)
        tok = login.headers.get("x-auth-token")
        if not tok:
            return {"reachable": False}
        st = requests.get(f"https://{ip}/api/v1.0/statistics",
                          headers={"x-auth-token": tok}, verify=False, timeout=8).json()
        dev = st[0]
        peer = (dev.get("wireless", {}).get("peers") or [{}])[0]
        local = (peer.get("local") or [{}])[0]
        lq = local.get("linkQuality", {})
        # puerto cableado más lento (bottleneck) + drops de recepción
        eth_speeds, eth_drops = [], 0
        for itf in dev.get("interfaces", []):
            spd = (itf.get("status") or {}).get("currentSpeed")
            if spd and ("-full" in spd or "-half" in spd):
                try: eth_speeds.append(int(spd.split("-")[0]))
                except Exception: pass
                eth_drops += int((itf.get("statistics") or {}).get("rxDropped", 0) or 0)
        return {
            "reachable": True,
            "linkState":   local.get("linkState", "?"),
            "signal":      lq.get("signal"),
            "idealSignal": lq.get("idealSignal"),
            "capacity":    (lq.get("capacity") or {}).get("combined"),
            "mcs":         (lq.get("mcs") or {}).get("rxIdx"),
            "eth_min":     min(eth_speeds) if eth_speeds else None,
            "eth_drops":   eth_drops,
            "ts":          ts(),
        }
    except Exception as e:
        return {"reachable": False, "error": type(e).__name__}

def _wave_alertkey(m, prev):
    """Estado discreto para detectar cambios (con histéresis en la señal)."""
    reachable = m.get("reachable", False)
    link = m.get("linkState", "?") if reachable else "?"
    eth = m.get("eth_min")
    eth_ok = (eth is None) or (eth >= 1000)
    sig = m.get("signal")
    if prev.get("signal_ok", True):
        signal_ok = (sig is None) or (sig >= WAVE_SIGNAL_WARN)
    else:  # venía degradada: recupera solo si supera el umbral OK (histéresis)
        signal_ok = (sig is not None) and (sig >= WAVE_SIGNAL_OK)
    return {"reachable": reachable, "link": link, "eth_ok": eth_ok, "signal_ok": signal_ok}

def _wave_resumen(lecturas):
    lines = ["📡 <b>Monitoreo enlace FFW activo</b>"]
    for ip, m in lecturas.items():
        name = WAVES_FFW[ip]
        if not m.get("reachable"):
            lines.append(f"• {name} ({ip}): SIN ACCESO"); continue
        cap = m.get("capacity") or 0
        eth = m.get("eth_min")
        ethtxt = "✅ 1000M" if (eth is None or eth >= 1000) else f"🟡 {eth}M (cuello de botella)"
        lines.append(f"• {name}: {m.get('linkState')} · señal {m.get('signal')} dBm · "
                     f"cap {int(cap/1000) if cap else '?'} Mbps · eth {ethtxt}")
    return "\n".join(lines)

def leer_waves_ffw():
    """Lee ambas Wave del FFW; primer paso = resumen, luego alerta SOLO por cambios."""
    global WAVES_STARTED
    if not WAVE_READ:
        return
    try:
        import urllib3; urllib3.disable_warnings()
    except Exception:
        pass
    lecturas = {ip: _wave_read(ip) for ip in WAVES_FFW}
    with LOCK:
        WAVES.clear(); WAVES.update(lecturas)

    if not WAVES_STARTED:   # baseline: avisa estado actual una vez, sin alertas de cambio
        WAVES_STARTED = True
        for ip, m in lecturas.items():
            WAVE_ALERTSTATE[ip] = _wave_alertkey(m, {})
        tg(_wave_resumen(lecturas))
        return

    for ip, m in lecturas.items():
        name = WAVES_FFW[ip]
        prev = WAVE_ALERTSTATE.get(ip, {})
        cur = _wave_alertkey(m, prev)
        msgs = []
        if cur["reachable"] != prev.get("reachable"):
            msgs.append(f"🟢 <b>{name}: acceso recuperado</b>" if cur["reachable"]
                        else f"🔴 <b>{name} SIN ACCESO</b> ({ip})")
        if cur["reachable"]:
            if cur["link"] != prev.get("link"):
                msgs.append(f"🟢 <b>Enlace FFW activo</b> — {name}" if cur["link"] == "active"
                            else f"🔴 <b>Enlace FFW caído</b> — {name}: linkState={m.get('linkState')}")
            if cur["eth_ok"] != prev.get("eth_ok"):
                msgs.append(f"🟢 <b>Ethernet OK</b> — {name}: puerto a {m.get('eth_min')} Mbps" if cur["eth_ok"]
                            else f"🟡 <b>Cuello de botella ETHERNET</b> — {name}: puerto a {m.get('eth_min')} Mbps "
                                 f"(esperado 1000). Revisar cable/PoE en sitio.")
            if cur["signal_ok"] != prev.get("signal_ok"):
                msgs.append(f"🟢 <b>Señal FFW recuperada</b> — {name}: {m.get('signal')} dBm" if cur["signal_ok"]
                            else f"🟡 <b>Señal FFW degradada</b> — {name}: {m.get('signal')} dBm "
                                 f"(ideal {m.get('idealSignal')})")
        for mm in msgs:
            tg(mm)
        WAVE_ALERTSTATE[ip] = cur

# ───────────────────────── CARGA INVENTARIO ─────────────────────────
def cargar():
    inv = json.load(open(INVENTORY, encoding="utf-8"))
    for ip, d in inv.items():
        d["ip"] = ip
        d["zona"] = zona(d.get("name"), d.get("radio_base"))
        d["is_backhaul"] = ip in BACKHAUL_ZONA or d.get("backhaul", False)
        d["estado"] = "desconocido"   # desconocido -> up / down / inactivo
        d["fails"] = 0
        d["oks"] = 0
        d["monitored"] = True         # False si nunca respondio (decomisionada)
        d["since"] = None
        d["baseline_down"] = False
        DEVICES[ip] = d
    print(f"Inventario: {len(DEVICES)} dispositivos cargados.")

# ───────────────────────── SUPRESION TOPOLOGICA ─────────────────────────
def backhaul_caido_de(z):
    """¿hay algun enlace backhaul de la zona z actualmente caido?"""
    for ip, zz in BACKHAUL_ZONA.items():
        if zz == z and DEVICES.get(ip, {}).get("estado") == "down":
            return True
    return False

# ───────────────────────── RONDA ─────────────────────────
def ronda(primera):
    ips = list(DEVICES.keys())
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        res = dict(zip(ips, ex.map(ping, ips)))

    transiciones = []
    with LOCK:
        for ip, vivo in res.items():
            d = DEVICES[ip]
            if primera:
                # baseline: definir estado inicial sin alertar
                if vivo:
                    d["estado"] = "up"; d["since"] = ts()
                else:
                    d["estado"] = "inactivo"; d["monitored"] = False; d["baseline_down"] = True
                continue

            if vivo:
                d["oks"] += 1; d["fails"] = 0
                # recuperacion (o revive una inactiva)
                if d["estado"] in ("down", "inactivo") and d["oks"] >= OK_THRESHOLD:
                    old = d["estado"]
                    d["estado"] = "up"; d["since"] = ts(); d["monitored"] = True
                    d["baseline_down"] = False
                    transiciones.append((d, old, "up"))
            else:
                d["fails"] += 1; d["oks"] = 0
                if d["estado"] == "up" and d["fails"] >= FAIL_THRESHOLD:
                    d["estado"] = "down"; d["since"] = ts()
                    transiciones.append((d, "up", "down"))

    # procesar transiciones (alertas) fuera del lock de calculo
    for d, old, new in transiciones:
        log_evento(d, old, new)
        alertar(d, new)

ALERT_TIPOS = {"sectorial", "enlace", "switch"}  # tipos que SI avisan a Telegram (dan servicio)

def alertar(d, new):
    # no spamear por equipos que no impactan clientes (UISP-Console=otro, estaciones, sin identificar)
    if d["tipo"] not in ALERT_TIPOS:
        print(f"  (sin alerta Telegram: {d['name']} es tipo '{d['tipo']}')")
        return
    z = d["zona"]; nombre = d["name"]; cli = d.get("clientes", 0)
    # supresion: si cae un SECTORIAL pero el ENLACE de su zona ya esta caido -> no spamear
    if new == "down" and d["tipo"] == "sectorial" and backhaul_caido_de(z):
        print(f"  (suprimido: {nombre} cae pero enlace de {z} ya esta caido)")
        return

    if new == "down":
        if d["is_backhaul"]:
            zona_aislada = BACKHAUL_ZONA.get(d["ip"], z)
            afect = sum(x.get("clientes", 0) for x in DEVICES.values()
                        if x["zona"] == zona_aislada and x["tipo"] == "sectorial")
            tg(f"🔴 <b>RADIO BASE {zona_aislada.upper()} AISLADA</b>\n"
               f"Enlace caído: {nombre} ({d['ip']})\n"
               f"~{afect} clientes sin servicio")
        elif d["tipo"] == "switch":
            tg(f"🔴 <b>Switch de torre caído</b>\n{nombre} ({d['ip']}) · {z}")
        else:
            extra = f" · ~{cli} clientes" if cli else ""
            tg(f"🔴 <b>Sectorial caído</b>\n{nombre} ({d['ip']}) · {z}{extra}")
    else:  # up
        tg(f"🟢 <b>Recuperado</b>\n{nombre} ({d['ip']}) · {z}")

# ───────────────────────── PUBLICAR ESTADO (dashboard) ─────────────────────────
def publicar():
    with LOCK:
        zonas = {}
        for d in DEVICES.values():
            if d["tipo"] == "estacion":   # no mostramos CPEs de cliente en el board
                continue
            zonas.setdefault(d["zona"], []).append({
                "ip": d["ip"], "name": d["name"], "tipo": d["tipo"],
                "estado": d["estado"], "is_backhaul": d["is_backhaul"],
                "clientes": d.get("clientes", 0), "since": d["since"],
            })
        snap = {
            "actualizado": ts(),
            "wans": dict(WANS),
            "waves": dict(WAVES),
            "zonas": zonas,
            "resumen": {
                "down": sum(1 for d in DEVICES.values() if d["estado"] == "down"),
                "up":   sum(1 for d in DEVICES.values() if d["estado"] == "up"),
                "inactivos": sum(1 for d in DEVICES.values() if d["estado"] == "inactivo"),
            },
        }
    json.dump(snap, open(STATUS_OUT, "w", encoding="utf-8"), ensure_ascii=False)
    return snap

# ───────────────────────── LOOP ─────────────────────────
def loop():
    global STARTED_AT
    STARTED_AT = ts()
    cargar()
    print(f"[{ts()}] Estableciendo baseline (primera ronda, sin alertar)...")
    ronda(primera=True)
    leer_wans()
    leer_waves_ffw()
    publicar()
    n_act = sum(1 for d in DEVICES.values() if d["monitored"])
    n_inact = sum(1 for d in DEVICES.values() if not d["monitored"])
    print(f"[{ts()}] Baseline listo: {n_act} vigilados, {n_inact} sin respuesta inicial (no alertan).")
    print(f"[{ts()}] Vigilando cada {INTERVAL_S}s. Dashboard: http://0.0.0.0:{WEB_PORT}/")
    ciclo = 0
    while True:
        time.sleep(INTERVAL_S)
        ronda(primera=False)
        ciclo += 1
        if ciclo % 3 == 0:   # leer WANs cada 3 ciclos (~1 min)
            leer_wans()
        if ciclo % WAVE_CHECK_EVERY == 0:   # leer enlace FFW cada ~5 min
            leer_waves_ffw()
        publicar()

# ───────────────────────── WEB ─────────────────────────
def crear_app():
    from flask import Flask, jsonify, Response
    app = Flask(__name__)

    @app.route("/api/status")
    def api_status():
        return jsonify(publicar())

    @app.route("/")
    def index():
        return Response(DASHBOARD_HTML, mimetype="text/html")

    return app

DASHBOARD_HTML = open(os.path.join(BASE_DIR, "dashboard.html"), encoding="utf-8").read() \
    if os.path.exists(os.path.join(BASE_DIR, "dashboard.html")) else "<h1>dashboard.html no encontrado</h1>"

# ─── arranque del colector (idempotente; un solo hilo aunque se importe 2 veces) ───
_collector_started = False
_collector_lock = threading.Lock()
def iniciar_collector():
    global _collector_started
    with _collector_lock:
        if _collector_started:
            return
        _collector_started = True
        threading.Thread(target=loop, daemon=True).start()
        # Colector de consumo (Fase 2) — hilo aparte que escribe en TimescaleDB
        try:
            import collector_traffic
            collector_traffic.start()
        except Exception as e:
            print("  [collector_traffic] no inició:", e)

# objeto WSGI para gunicorn:  gunicorn vigilante:app
import sys as _sys
app = crear_app()
if "--once" not in _sys.argv:
    iniciar_collector()   # se ejecuta al importar (gunicorn) y en modo dev

if __name__ == "__main__":
    if "--once" in _sys.argv:
        # modo prueba: una sola ronda baseline + imprime, sin web ni alertas
        cargar(); ronda(primera=True); leer_wans()
        snap = publicar()
        print(json.dumps(snap["resumen"], indent=2))
        for z, devs in snap["zonas"].items():
            up = sum(1 for d in devs if d["estado"] == "up")
            print(f"  {z}: {up}/{len(devs)} arriba")
        _sys.exit(0)
    # modo desarrollo (servidor Flask). En produccion se usa gunicorn (ver Dockerfile).
    app.run(host="0.0.0.0", port=WEB_PORT, threaded=True)
