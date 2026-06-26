# -*- coding: utf-8 -*-
"""Proveedor OTP Mock para desarrollo y pruebas automatizadas (W5.2).

NO envía nada externo: guarda el último código por teléfono en memoria para que
las pruebas puedan recuperarlo. Jamás usar en producción.
"""
import logging

from .otp_base import OtpProvider

_logger = logging.getLogger("coc.gateway.otp")


class MockOtpProvider(OtpProvider):
    name = "mock"

    def __init__(self):
        self.sent: dict[str, str] = {}   # phone -> último código (solo pruebas)
        self.calls: list[tuple[str, str, str]] = []

    def send(self, phone: str, code: str, channel: str = "whatsapp") -> bool:
        self.sent[phone] = code
        self.calls.append((phone, channel, code))
        _logger.info("MOCK OTP -> phone=%s channel=%s (code oculto en prod-logs)", phone, channel)
        return True

    # Helpers de prueba
    def last_code(self, phone: str) -> str | None:
        return self.sent.get(phone)
