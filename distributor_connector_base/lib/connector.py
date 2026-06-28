"""Contrato de conector + registro. Agregar un distribuidor = implementar esta
interfaz y registrarla con @register_connector. El motor resuelve por clave; NUNCA
con `if distributor == "x"`.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Type

from .dto import NormalizedProduct
from .exceptions import CompatibilityError
from .version import ENGINE_VERSION, is_compatible

_logger = logging.getLogger(__name__)

# Registro global de conectores: connector_key -> clase
CONNECTOR_REGISTRY: Dict[str, Type["DistributorConnector"]] = {}


def register_connector(key: str, requires_engine: str = ">=1.0,<2.0"):
    """Decorador de registro. Valida compatibilidad de versión del motor."""
    def deco(cls: Type["DistributorConnector"]):
        if not is_compatible(ENGINE_VERSION, requires_engine):
            raise CompatibilityError(
                "Conector %r requiere motor %s, hay %s" % (key, requires_engine, ENGINE_VERSION))
        cls.connector_key = key
        cls.requires_engine = requires_engine
        if key in CONNECTOR_REGISTRY and CONNECTOR_REGISTRY[key] is not cls:
            _logger.warning("connector_key duplicado, se sobreescribe: %s", key)
        CONNECTOR_REGISTRY[key] = cls
        _logger.info("Conector registrado: %s (%s)", key, getattr(cls, "version", "?"))
        return cls
    return deco


def get_connector_class(key: str) -> Optional[Type["DistributorConnector"]]:
    return CONNECTOR_REGISTRY.get(key)


def available_connectors() -> List[str]:
    return sorted(CONNECTOR_REGISTRY.keys())


class DistributorConnector(ABC):
    """Interfaz que TODO distribuidor implementa. Recibe `config` (dict del backend).

    El núcleo solo conoce estos métodos; cada conector encapsula SU API, auth,
    paginación, rate-limit y mapeo (`normalize`).
    """

    connector_key: str = ""
    requires_engine: str = ">=1.0,<2.0"
    version: str = "1.0.0"

    def __init__(self, config: Dict):
        self.config = config or {}

    # --- ciclo de vida ---
    @abstractmethod
    def authenticate(self) -> Optional[str]:
        """Obtiene/renueva el token o credencial de sesión."""

    # --- consulta ---
    @abstractmethod
    def search(self, query: str, filters: Optional[Dict] = None, page: int = 1) -> List[NormalizedProduct]:
        """Búsqueda (listado, ligera) → lista de NormalizedProduct."""

    @abstractmethod
    def get_product(self, ref: str) -> NormalizedProduct:
        """Detalle completo (enriquecido) de un producto por su referencia externa."""

    @abstractmethod
    def get_price_stock(self, refs: List[str]) -> Dict[str, Dict]:
        """Precio/stock autoritativo y ligero para varias refs: {ref: {price, stock}}."""

    # --- mapeo ---
    @abstractmethod
    def normalize(self, raw: Dict) -> NormalizedProduct:
        """Mapea el JSON crudo del proveedor → NormalizedProduct."""
