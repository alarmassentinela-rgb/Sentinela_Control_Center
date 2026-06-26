# -*- coding: utf-8 -*-
"""Notificador de seguridad desacoplado (nuevos inicios de sesión, etc.).

Igual que el OTP: interfaz + Mock para dev/test; la implementación real (WhatsApp
vía EvoApi / Odoo notify) se cablea por configuración sin tocar la lógica.
"""
from abc import ABC, abstractmethod


class LoginNotifier(ABC):
    @abstractmethod
    def notify_new_login(self, identity, device_label: str, ip: str | None) -> bool:
        raise NotImplementedError
