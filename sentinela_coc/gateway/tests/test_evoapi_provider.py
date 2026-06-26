# -*- coding: utf-8 -*-
"""Integración EvoApi — resiliencia y seguridad del driver (transporte mockeado)."""
import logging

import httpx

from app.providers.circuit_breaker import CircuitBreaker
from app.providers.otp_evoapi import EvoApiOtpProvider

API_KEY = "super-secret-apikey"
CODE = "424242"
PHONE = "+528680000001"


def _provider(handler, **kw):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    kw.setdefault("backoff", 0)
    return EvoApiOtpProvider("http://evo.local", API_KEY, "inst1", client=client, **kw)


def test_send_success():
    calls = {"n": 0}

    def h(req):
        calls["n"] += 1
        return httpx.Response(200, json={"key": {"id": "x"}})

    assert _provider(h).send(PHONE, CODE) is True
    assert calls["n"] == 1


def test_send_retries_then_success():
    calls = {"n": 0}

    def h(req):
        calls["n"] += 1
        return httpx.Response(500) if calls["n"] < 2 else httpx.Response(200, json={"ok": 1})

    assert _provider(h, retries=2).send(PHONE, CODE) is True
    assert calls["n"] == 2


def test_send_all_fail_returns_false():
    assert _provider(lambda req: httpx.Response(500), retries=2).send(PHONE, CODE) is False


def test_circuit_breaker_opens_and_skips_transport():
    calls = {"n": 0}

    def h(req):
        calls["n"] += 1
        return httpx.Response(500)

    br = CircuitBreaker(fail_threshold=1, cooldown_sec=999)
    p = _provider(h, retries=0, breaker=br)
    assert p.send(PHONE, CODE) is False        # 1 fallo -> abre (umbral 1)
    n1 = calls["n"]
    assert p.send(PHONE, CODE) is False         # circuito ABIERTO -> no llama al transporte
    assert calls["n"] == n1
    assert br.state == "open"


def test_health_ok_and_fail():
    assert _provider(lambda req: httpx.Response(200, text='{"instance":{"state":"open"}}')).health()["healthy"] is True
    assert _provider(lambda req: httpx.Response(500, text="err")).health()["healthy"] is False


def test_no_secret_or_otp_in_logs_on_failure(caplog):
    p = _provider(lambda req: httpx.Response(500), retries=1)
    with caplog.at_level(logging.DEBUG, logger="coc.gateway.otp"):
        p.send(PHONE, CODE)
    assert CODE not in caplog.text
    assert API_KEY not in caplog.text


def test_no_secret_or_otp_in_logs_on_success(caplog):
    p = _provider(lambda req: httpx.Response(200, json={"ok": 1}))
    with caplog.at_level(logging.DEBUG, logger="coc.gateway.otp"):
        assert p.send(PHONE, CODE) is True
    assert CODE not in caplog.text
    assert API_KEY not in caplog.text
    assert PHONE not in caplog.text          # el teléfono va enmascarado
