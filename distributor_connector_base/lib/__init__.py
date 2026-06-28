"""Catalog Engine — librería pura (sin dependencias de Odoo).

Reutilizable, tipada y testeable de forma aislada. La capa Odoo (models/) la usa.
"""
from . import version
from . import exceptions
from . import dto
from . import events
from . import resilience
from . import instrumentation
from . import connector

ENGINE_VERSION = version.ENGINE_VERSION
