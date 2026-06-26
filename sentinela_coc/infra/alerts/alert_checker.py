#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Chequeador de alertas del COC Gateway → Telegram (observabilidad, W RC).

Sondea /health, /v1/providers/health y /metrics del gateway y envía alerta a
Telegram cuando se incumple una condición. Sin dependencias (stdlib). Programar
por cron cada 1–5 min. Config por entorno:
  GW_BASE_URL          (default http://127.0.0.1:8400)
  TELEGRAM_BOT_TOKEN   (token del bot de alertas)
  TELEGRAM_CHAT_ID     (chat/grupo destino)
NUNCA imprime ni envía secretos/OTP.
"""
import json
import os
import urllib.parse
import urllib.request

GW = os.environ.get("GW_BASE_URL", "http://127.0.0.1:8400")
TG_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
TIMEOUT = 8


def _get(path):
    try:
        with urllib.request.urlopen(GW + path, timeout=TIMEOUT) as r:
            return r.status, r.read().decode()
    except Exception as e:
        return None, str(e)[:120]


def _telegram(msg):
    if not TG_TOKEN or not TG_CHAT:
        print("[sin config Telegram] " + msg)
        return
    data = urllib.parse.urlencode({"chat_id": TG_CHAT, "text": msg}).encode()
    try:
        urllib.request.urlopen(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data=data, timeout=TIMEOUT)
    except Exception as e:
        print("error telegram:", type(e).__name__)


def _parse_metrics(text):
    m = {}
    for line in text.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.rsplit(" ", 1)
        if len(parts) == 2:
            try:
                m[parts[0]] = float(parts[1])
            except ValueError:
                pass
    return m


def main():
    alerts = []
    st, _ = _get("/health")
    if st != 200:
        alerts.append(f"🔴 Gateway no responde (/health={st})")

    st, body = _get("/v1/providers/health")
    if st == 200:
        try:
            if not json.loads(body).get("healthy"):
                alerts.append("🔴 Proveedor OTP (WhatsApp) NO disponible")
        except Exception:
            pass

    st, body = _get("/metrics")
    if st == 200:
        m = _parse_metrics(body)
        if m.get("otp_provider_up", 1) == 0:
            alerts.append("🟠 otp_provider_up=0 (instancia WhatsApp caída)")
        co = m.get('otp_send_total{result="circuit_open"}', 0)
        if co > 0:
            alerts.append(f"🟠 Circuit breaker OTP abierto ({int(co)} envíos omitidos)")
        fail = m.get('otp_send_total{result="fail"}', 0)
        if fail > 0:
            alerts.append(f"🟠 Fallos de envío OTP acumulados: {int(fail)}")

    for a in alerts:
        _telegram("[COC] " + a)
    print("OK: sin alertas" if not alerts else f"{len(alerts)} alerta(s) enviada(s)")


if __name__ == "__main__":
    main()
