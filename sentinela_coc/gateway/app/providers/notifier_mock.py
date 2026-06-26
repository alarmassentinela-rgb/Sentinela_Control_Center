# -*- coding: utf-8 -*-
"""Notificador Mock (dev/test): registra los avisos en memoria."""
import logging

from .notifier_base import LoginNotifier

_logger = logging.getLogger("coc.gateway.notify")


class MockLoginNotifier(LoginNotifier):
    def __init__(self):
        self.events: list[dict] = []

    def notify_new_login(self, identity, device_label, ip):
        self.events.append({"partner_id": getattr(identity, "partner_id", None),
                            "device": device_label, "ip": ip})
        _logger.info("NEW LOGIN notify partner=%s device=%s ip=%s",
                     getattr(identity, "partner_id", None), device_label, ip)
        return True
