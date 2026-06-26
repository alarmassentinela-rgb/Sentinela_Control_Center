# -*- coding: utf-8 -*-
"""Interfaz desacoplada de proveedor de OTP (W5.2).

El Gateway NO depende de un proveedor concreto. EvoApi será solo la PRIMERA
implementación real; en desarrollo/pruebas se usa MockOtpProvider.
"""
from abc import ABC, abstractmethod


class OtpProvider(ABC):
    """Envía un código OTP por un canal (whatsapp/sms). No genera ni valida el
    código (eso es responsabilidad del servicio OTP): solo lo entrega."""

    name: str = "base"

    @abstractmethod
    def send(self, phone: str, code: str, channel: str = "whatsapp") -> bool:
        """Entrega el código. Devuelve True si se aceptó para envío."""
        raise NotImplementedError
