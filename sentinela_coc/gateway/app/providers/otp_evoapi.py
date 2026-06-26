# -*- coding: utf-8 -*-
"""Proveedor OTP EvoApi (WhatsApp) — PRIMERA implementación real (se cablea luego).

Stub: la integración real se completa cuando el flujo esté 100% validado con el
Mock. Mantiene la MISMA interfaz, así que activarlo es solo configuración
(COC_OTP_PROVIDER=evoapi).
"""
import logging

from .otp_base import OtpProvider

_logger = logging.getLogger("coc.gateway.otp")


class EvoApiOtpProvider(OtpProvider):
    name = "evoapi"

    def __init__(self, base_url: str, api_key: str, instance: str):
        self.base_url = base_url
        self.api_key = api_key
        self.instance = instance

    def send(self, phone: str, code: str, channel: str = "whatsapp") -> bool:
        # TODO(W5 EvoApi): POST a EvoApi con plantilla transaccional aprobada.
        raise NotImplementedError("EvoApi se cablea tras validar el flujo con Mock")
