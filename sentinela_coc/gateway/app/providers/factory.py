# -*- coding: utf-8 -*-
"""Factoría de proveedor OTP — elige la implementación por configuración."""
from ..config import settings
from .notifier_base import LoginNotifier
from .notifier_mock import MockLoginNotifier
from .otp_base import OtpProvider
from .otp_mock import MockOtpProvider


_singleton: OtpProvider | None = None
_notifier: LoginNotifier | None = None


def get_otp_provider() -> OtpProvider:
    """Devuelve el proveedor configurado. Mock por defecto (desarrollo/pruebas)."""
    global _singleton
    if _singleton is not None:
        return _singleton
    if settings.otp_provider == "evoapi":
        from .otp_evoapi import EvoApiOtpProvider
        _singleton = EvoApiOtpProvider(settings.wa_base_url, settings.wa_api_key, settings.wa_instance)
    else:
        _singleton = MockOtpProvider()
    return _singleton


def get_notifier() -> LoginNotifier:
    """Notificador de seguridad (nuevos logins). Mock por defecto; EvoApi/Odoo después."""
    global _notifier
    if _notifier is None:
        _notifier = MockLoginNotifier()
    return _notifier
