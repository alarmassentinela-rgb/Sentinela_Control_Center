"""distributor.backend — configuración por distribuidor (R3), credenciales seguras
(R5) y resolución del conector registrado (R4). Sin lógica específica de proveedor.
"""
from __future__ import annotations

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..lib import connector as conn_lib
from ..lib import version as ver_lib
from ..lib.exceptions import CatalogError, CompatibilityError

_logger = logging.getLogger(__name__)


class DistributorBackend(models.Model):
    _name = "distributor.backend"
    _description = "Distribuidor (backend del Motor de Catálogo)"
    _order = "name"

    name = fields.Char(required=True)
    connector_key = fields.Selection(
        selection="_sel_connectors", required=True,
        help="Conector instalado que atiende a este distribuidor (registro de conectores).")
    active = fields.Boolean(default=True)
    partner_id = fields.Many2one("res.partner", string="Proveedor (contacto)")
    currency_id = fields.Many2one(
        "res.currency", string="Moneda",
        default=lambda self: self.env.ref("base.USD", raise_if_not_found=False))
    api_url = fields.Char(string="URL de la API")

    # --- Resiliencia (R5) ---
    rate_limit = fields.Integer(string="Llamadas/min", default=280)
    timeout = fields.Integer(string="Timeout (s)", default=30)
    retries = fields.Integer(string="Reintentos", default=5)
    circuit_failure_threshold = fields.Integer(string="Umbral circuit breaker", default=5)
    circuit_recovery_timeout = fields.Integer(string="Recuperación circuit (s)", default=30)

    # --- Caché TTL (R3), en minutos ---
    cache_ttl_price = fields.Integer(string="TTL precio (min)", default=720)
    cache_ttl_stock = fields.Integer(string="TTL stock (min)", default=120)
    cache_ttl_enrichment = fields.Integer(string="TTL enriquecimiento (min)", default=10080)

    # --- Políticas (R3) ---
    image_policy = fields.Selection(
        [("url", "Solo URL (CDN)"), ("local", "Local (binario)"), ("hybrid", "Híbrido")],
        default="url", string="Política de imágenes")
    document_policy = fields.Selection(
        [("url", "Solo URL"), ("local", "Local")], default="url", string="Política de documentos")
    update_strategy = fields.Selection(
        [("listing", "Barrido por listado"), ("detail", "Detalle 1×1"), ("delta", "Delta/incremental")],
        default="listing", string="Estrategia de actualización")
    sync_enabled = fields.Boolean(string="Sincronización activa", default=True)

    # --- Versionado / compatibilidad (R2) ---
    engine_version = fields.Char(compute="_compute_versions", string="Versión del motor")
    connector_version = fields.Char(compute="_compute_versions", string="Versión del conector")
    connector_compatible = fields.Boolean(compute="_compute_versions", string="Compatible")

    credential_rotated_on = fields.Datetime(string="Credenciales rotadas el", readonly=True)

    _sql_constraints = [
        ("connector_key_uniq", "unique(connector_key)",
         "Ya existe un distribuidor con ese conector."),
    ]

    @api.model
    def _sel_connectors(self):
        keys = conn_lib.available_connectors()
        return [(k, k) for k in keys] or [("none", _("(sin conectores instalados)"))]

    @api.depends("connector_key")
    def _compute_versions(self):
        for rec in self:
            rec.engine_version = ver_lib.ENGINE_VERSION
            cls = conn_lib.get_connector_class(rec.connector_key or "")
            rec.connector_version = getattr(cls, "version", False) if cls else False
            if cls:
                rec.connector_compatible = ver_lib.is_compatible(
                    ver_lib.ENGINE_VERSION, getattr(cls, "requires_engine", ">=1.0,<2.0"))
            else:
                rec.connector_compatible = False

    # ------------------------------------------------------------------
    # Credenciales seguras (R5): viven en ir.config_parameter, NUNCA en el modelo.
    # ------------------------------------------------------------------
    def _secret_key(self, name: str) -> str:
        self.ensure_one()
        return "distributor_backend.%s.%s" % (self.id, name)

    def get_secret(self, name: str):
        self.ensure_one()
        return self.env["ir.config_parameter"].sudo().get_param(self._secret_key(name))

    def set_secret(self, name: str, value: str):
        self.ensure_one()
        self.env["ir.config_parameter"].sudo().set_param(self._secret_key(name), value or "")

    def rotate_credentials(self):
        """Invalida token cacheado y marca la rotación (R5)."""
        for rec in self:
            rec.set_secret("token_cache", "")
            rec.set_secret("token_expiry", "0")
            rec.credential_rotated_on = fields.Datetime.now()
        return True

    # ------------------------------------------------------------------
    # Resolución del conector (R4)
    # ------------------------------------------------------------------
    def _connector_config(self) -> dict:
        self.ensure_one()
        return {
            "backend_id": self.id,
            "connector_key": self.connector_key,
            "api_url": self.api_url,
            "rate_limit": self.rate_limit,
            "timeout": self.timeout,
            "retries": self.retries,
            "circuit_failure_threshold": self.circuit_failure_threshold,
            "circuit_recovery_timeout": self.circuit_recovery_timeout,
            "ttl": {
                "price": self.cache_ttl_price,
                "stock": self.cache_ttl_stock,
                "enrichment": self.cache_ttl_enrichment,
            },
            "image_policy": self.image_policy,
            "document_policy": self.document_policy,
            "update_strategy": self.update_strategy,
            "get_secret": self.get_secret,
            "set_secret": self.set_secret,
        }

    def get_connector(self):
        """Instancia el conector registrado para este backend (o UserError claro)."""
        self.ensure_one()
        cls = conn_lib.get_connector_class(self.connector_key or "")
        if not cls:
            raise UserError(_("No hay conector instalado para la clave '%s'.") % self.connector_key)
        if not ver_lib.is_compatible(ver_lib.ENGINE_VERSION, getattr(cls, "requires_engine", ">=1.0,<2.0")):
            raise CompatibilityError(
                _("El conector '%s' no es compatible con el motor %s.")
                % (self.connector_key, ver_lib.ENGINE_VERSION))
        return cls(self._connector_config())

    def action_test_connection(self):
        self.ensure_one()
        try:
            connector = self.get_connector()
            connector.authenticate()
            msg, kind = _("Conexión exitosa con %s.") % self.name, "success"
        except (CatalogError, UserError) as e:
            msg, kind = str(e), "warning"
        except Exception as e:  # noqa: BLE001
            _logger.exception("Test de conexión falló")
            msg, kind = _("Error: %s") % e, "danger"
        return {
            "type": "ir.actions.client", "tag": "display_notification",
            "params": {"title": _("Prueba de conexión"), "message": msg, "type": kind, "sticky": False},
        }
