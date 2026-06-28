"""Eventos persistidos (R3/R8): catalog.event. La capa Odoo persiste y reenvía al
EventBus en proceso (suscriptores: automatizaciones, IA, notificaciones a futuro).
"""
from __future__ import annotations

import json

from odoo import api, fields, models

from ..lib import events as evt


class CatalogEvent(models.Model):
    _name = "catalog.event"
    _description = "Evento del Motor de Catálogo"
    _order = "id desc"

    name = fields.Selection(
        [(e, e) for e in sorted(evt.ALL_EVENTS)], required=True, index=True)
    backend_key = fields.Char(index=True)
    payload = fields.Text(help="JSON con el detalle del evento.")
    source = fields.Selection(
        [("cron", "Cron"), ("api", "API"), ("wizard", "Asistente"), ("user", "Usuario"),
         ("system", "Sistema")], default="system")
    occurred_at = fields.Datetime(default=fields.Datetime.now, index=True)

    @api.model
    def emit(self, name, backend_key="", payload=None, source="system"):
        """Persiste el evento y lo publica en el bus en proceso (handlers suscritos)."""
        if name not in evt.ALL_EVENTS:
            raise ValueError("Evento desconocido: %r" % name)
        payload = payload or {}
        rec = self.sudo().create({
            "name": name, "backend_key": backend_key or "",
            "payload": json.dumps(payload, ensure_ascii=False, default=str), "source": source,
        })
        evt.default_bus.publish(evt.Event(
            name=name, backend_key=backend_key or "", payload=payload, source=source,
            occurred_at=fields.Datetime.to_string(rec.occurred_at)))
        return rec
