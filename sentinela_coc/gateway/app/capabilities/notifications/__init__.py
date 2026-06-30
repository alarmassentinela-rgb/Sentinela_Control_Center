# -*- coding: utf-8 -*-
"""Capacidad Notificaciones (Cobranza) — confirmación de pago (S2-012).

Reusa el canal existente; no crea mensajería nueva.
"""
from .consumer import (
    FakeNotificationChannel,
    NotificationPort,
    NotificationsConsumer,
    NotifyOutcome,
    OdooNotificationChannel,
)

__all__ = [
    "NotificationsConsumer", "NotificationPort", "NotifyOutcome",
    "FakeNotificationChannel", "OdooNotificationChannel",
]
