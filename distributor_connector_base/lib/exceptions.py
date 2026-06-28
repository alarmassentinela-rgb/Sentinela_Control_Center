"""Jerarquía de excepciones del Catalog Engine.

Todo error del motor/conectores hereda de CatalogError → captura uniforme y
mapeo a métricas/eventos sin depender del distribuidor concreto.
"""
from __future__ import annotations


class CatalogError(Exception):
    """Base de todos los errores del Motor de Catálogo."""


class ConfigurationError(CatalogError):
    """Configuración inválida o incompleta (backend, credenciales, etc.)."""


class CompatibilityError(CatalogError):
    """El conector no es compatible con la versión del motor."""


class NormalizationError(CatalogError):
    """El payload del proveedor no pudo mapearse al NormalizedProduct."""


class ConnectorError(CatalogError):
    """Base de errores propios de un conector/distribuidor."""


class AuthError(ConnectorError):
    """Fallo de autenticación con el distribuidor."""


class RateLimitError(ConnectorError):
    """El distribuidor respondió 429 / se excedió la cuota."""


class UpstreamUnavailableError(ConnectorError):
    """El distribuidor no está disponible (5xx, timeout, red)."""


class CircuitOpenError(ConnectorError):
    """El circuit breaker está abierto: no se intenta la llamada."""
