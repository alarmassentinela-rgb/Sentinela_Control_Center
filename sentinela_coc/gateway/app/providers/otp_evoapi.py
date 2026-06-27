# -*- coding: utf-8 -*-
"""Proveedor OTP EvoApi (WhatsApp) — PRIMERA implementación real.

Misma interfaz que el Mock (intercambiable por config). Incluye health check,
métricas (disponibilidad/latencia), circuit breaker, reintentos controlados y
manejo seguro de errores. NUNCA registra el OTP ni la api_key.
"""
import logging
import time

import httpx

from ..metrics import metrics
from ..services.phone import to_evoapi_mx
from .circuit_breaker import CircuitBreaker
from .otp_base import OtpProvider

_logger = logging.getLogger("coc.gateway.otp")

DEFAULT_TEMPLATE = ("Tu código de acceso Sentinela es: {code}\n"
                    "Vence en 5 minutos. No lo compartas con nadie.")


def _mask(phone: str) -> str:
    if phone and len(phone) > 7:
        return phone[:5] + "…" + phone[-2:]
    return "***"


class EvoApiOtpProvider(OtpProvider):
    name = "evoapi"

    def __init__(self, base_url, api_key, instance, template=None, timeout=8.0,
                 retries=2, backoff=0.5, breaker=None, client=None):
        self.base_url = (base_url or "").rstrip("/")
        self._api_key = api_key            # nunca se loguea
        self.instance = instance
        self.template = template or DEFAULT_TEMPLATE
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.breaker = breaker or CircuitBreaker()
        self._client = client              # inyectable en pruebas

    def _http(self):
        return self._client or httpx.Client(timeout=self.timeout)

    def _headers(self):
        return {"apikey": self._api_key, "Content-Type": "application/json"}

    def health(self) -> dict:
        try:
            r = self._http().get(f"{self.base_url}/instance/connectionState/{self.instance}",
                                 headers=self._headers())
            txt = (r.text or "").lower()
            ok = r.status_code == 200 and ("open" in txt or "connected" in txt)
            metrics.set_gauge("otp_provider_up", 1 if ok else 0)
            return {"provider": "evoapi", "healthy": ok, "status_code": r.status_code}
        except Exception as e:
            metrics.set_gauge("otp_provider_up", 0)
            _logger.warning("evoapi health error: %s", type(e).__name__)   # sin secretos
            return {"provider": "evoapi", "healthy": False, "error": type(e).__name__}

    def send(self, phone: str, code: str, channel: str = "whatsapp") -> bool:
        if not self.breaker.allow():
            metrics.inc("otp_send_total", result="circuit_open")
            _logger.warning("evoapi circuit OPEN, envío omitido para %s", _mask(phone))
            return False

        url = f"{self.base_url}/message/sendText/{self.instance}"
        number = to_evoapi_mx(phone)                       # E.164 MX (52+10) — formato EvoApi
        body = {"number": number, "text": self.template.format(code=code)}   # code NO se loguea
        attempt = 0
        while True:
            attempt += 1
            t0 = time.monotonic()
            try:
                r = self._http().post(url, json=body, headers=self._headers())
                dt = (time.monotonic() - t0) * 1000.0
                metrics.observe_latency(dt)
                if r.status_code in (200, 201):
                    self.breaker.record_success()
                    metrics.inc("otp_send_total", result="ok")
                    metrics.set_gauge("otp_provider_up", 1)
                    _logger.info("evoapi OTP enviado a %s (%.0f ms)", _mask(phone), dt)
                    return True
                raise httpx.HTTPStatusError(f"status {r.status_code}", request=r.request, response=r)
            except Exception as e:
                if attempt > self.retries:
                    self.breaker.record_failure()
                    metrics.inc("otp_send_total", result="fail")
                    metrics.set_gauge("otp_provider_up", 0)
                    _logger.error("evoapi envío falló para %s: %s", _mask(phone), type(e).__name__)
                    return False
                if self.backoff:
                    time.sleep(self.backoff * attempt)   # backoff lineal (0 en pruebas)
