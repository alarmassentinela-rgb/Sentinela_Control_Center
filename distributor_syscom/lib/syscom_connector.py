"""SyscomConnector — conector de REFERENCIA del Motor de Catálogo.

Implementa el contrato DistributorConnector usando la infraestructura del SDK
(rate-limit, circuit breaker, backoff vía Session/Retry). Encapsula auth OAuth con
caché de token, mapeo de errores, métricas por endpoint y normalización (lib.mapping).

Todo método público está documentado. Cualquier desarrollador puede construir un
nuevo conector copiando este patrón (ver README.md y MAPEO_NORMALIZACION.md).
"""
from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

import requests
from requests.adapters import HTTPAdapter

try:  # urllib3 ubicación según versión
    from urllib3.util.retry import Retry
except Exception:  # pragma: no cover
    from requests.packages.urllib3.util.retry import Retry  # type: ignore

from odoo.addons.distributor_connector_base.lib import resilience
from odoo.addons.distributor_connector_base.lib.connector import (
    DistributorConnector, register_connector)
from odoo.addons.distributor_connector_base.lib.dto import NormalizedProduct
from odoo.addons.distributor_connector_base.lib.exceptions import (
    AuthError, CircuitOpenError, ConnectorError, NormalizationError,
    RateLimitError, UpstreamUnavailableError)

from . import mapping, quality

_logger = logging.getLogger(__name__)

OAUTH_URL = "https://developers.syscom.mx/oauth/token"
DEFAULT_API = "https://developers.syscom.mx/api/v1"


@register_connector("syscom", requires_engine=">=1.0,<2.0")
class SyscomConnector(DistributorConnector):
    """Conector para el distribuidor Syscom (developers.syscom.mx)."""

    version = "1.0.0"

    def __init__(self, config: Dict):
        super().__init__(config)
        self.api_base = (config.get("api_url") or DEFAULT_API).rstrip("/")
        self.timeout = config.get("timeout") or 30
        self.retries = config.get("retries") or 5
        self._get_secret = config.get("get_secret") or (lambda k: None)
        self._set_secret = config.get("set_secret") or (lambda k, v: None)
        self._rl = resilience.RateLimiter(config.get("rate_limit") or 280)
        self._cb = resilience.CircuitBreaker(
            config.get("circuit_failure_threshold") or 5,
            config.get("circuit_recovery_timeout") or 30)
        self._session = None
        # métricas por endpoint
        self.metrics: Dict[str, Dict] = {}

    # ------------------------------------------------------------------
    # Sesión HTTP (keep-alive + reintentos urllib3). Inyectable en pruebas.
    # ------------------------------------------------------------------
    def _build_session(self) -> requests.Session:
        s = requests.Session()
        retry = Retry(total=self.retries, backoff_factor=1.0,
                      status_forcelist=[429, 500, 502, 503, 504], raise_on_status=False)
        adapter = HTTPAdapter(max_retries=retry, pool_connections=16, pool_maxsize=16)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        return s

    @property
    def session(self) -> requests.Session:
        if self._session is None:
            self._session = self._build_session()
        return self._session

    # ------------------------------------------------------------------
    # Autenticación (OAuth client_credentials con caché de token ~365 días)
    # ------------------------------------------------------------------
    def authenticate(self, force: bool = False) -> str:
        """Devuelve un access_token válido. Reutiliza el cacheado salvo `force`.
        Lanza AuthError si faltan credenciales o el OAuth falla."""
        token = self._get_secret("token_cache")
        try:
            expiry = float(self._get_secret("token_expiry") or 0)
        except (TypeError, ValueError):
            expiry = 0.0
        if token and not force and (expiry - time.time()) > 86400:
            return token
        cid = self._get_secret("client_id")
        sec = self._get_secret("client_secret")
        if not cid or not sec:
            raise AuthError("Faltan client_id/client_secret en el backend Syscom")
        try:
            r = requests.post(OAUTH_URL, data={
                "client_id": cid, "client_secret": sec, "grant_type": "client_credentials",
            }, timeout=self.timeout)
        except requests.RequestException as e:
            raise UpstreamUnavailableError("OAuth Syscom: %s" % e)
        if r.status_code != 200:
            raise AuthError("OAuth Syscom HTTP %s" % r.status_code)
        try:
            data = r.json()
        except ValueError:
            raise AuthError("OAuth Syscom: respuesta no-JSON")
        token = data.get("access_token")
        if not token:
            raise AuthError("OAuth Syscom sin access_token")
        self._set_secret("token_cache", token)
        self._set_secret("token_expiry", str(time.time() + float(data.get("expires_in") or 3600)))
        return token

    # ------------------------------------------------------------------
    # Métricas por endpoint (objetivo #5)
    # ------------------------------------------------------------------
    def _metric(self, endpoint: str) -> Dict:
        return self.metrics.setdefault(endpoint, {
            "count": 0, "total_ms": 0.0, "max_ms": 0.0, "errors": 0, "retries": 0,
            "cache_hit": 0, "cache_miss": 0})

    def metrics_summary(self) -> Dict[str, Dict]:
        """Resumen por endpoint: count, avg_ms, max_ms, errors, retries, cache_hit/miss."""
        out = {}
        for ep, m in self.metrics.items():
            out[ep] = dict(m, avg_ms=round(m["total_ms"] / m["count"], 2) if m["count"] else 0.0,
                           max_ms=round(m["max_ms"], 2))
        return out

    # ------------------------------------------------------------------
    # Núcleo HTTP con resiliencia + mapeo de errores (objetivo #4)
    # ------------------------------------------------------------------
    def _get(self, endpoint: str, path: str, params: Optional[Dict] = None,
             _retry_on_401: bool = True) -> Dict:
        m = self._metric(endpoint)
        self._rl.acquire()

        def _do():
            headers = {"Authorization": "Bearer %s" % self.authenticate()}
            resp = self.session.get(self.api_base + path, headers=headers,
                                    params=params, timeout=self.timeout)
            if resp.status_code == 429:
                raise RateLimitError("HTTP 429 Syscom")
            if resp.status_code >= 500:
                raise UpstreamUnavailableError("HTTP %s Syscom" % resp.status_code)
            return resp

        t0 = time.perf_counter()
        try:
            resp = self._cb.call(_do)
        except (CircuitOpenError, RateLimitError, UpstreamUnavailableError):
            m["errors"] += 1
            raise
        except requests.Timeout:
            m["errors"] += 1
            raise UpstreamUnavailableError("Timeout en %s" % path)
        except requests.RequestException as e:
            m["errors"] += 1
            raise UpstreamUnavailableError("Red: %s" % e)
        finally:
            ms = (time.perf_counter() - t0) * 1000.0
            m["count"] += 1
            m["total_ms"] += ms
            m["max_ms"] = max(m["max_ms"], ms)

        # contador de reintentos (historial urllib3, si disponible)
        try:
            hist = getattr(getattr(resp, "raw", None), "retries", None)
            if hist and getattr(hist, "history", None):
                m["retries"] += len(hist.history)
        except Exception:  # noqa: BLE001
            pass

        if resp.status_code == 401 and _retry_on_401:
            self.authenticate(force=True)  # token expirado → renovar y reintentar 1 vez
            return self._get(endpoint, path, params, _retry_on_401=False)
        if resp.status_code != 200:
            m["errors"] += 1
            raise ConnectorError("HTTP %s en %s" % (resp.status_code, path))
        try:
            return resp.json()
        except ValueError:
            m["errors"] += 1
            raise UpstreamUnavailableError("JSON inválido en %s" % path)

    # ------------------------------------------------------------------
    # Contrato DistributorConnector
    # ------------------------------------------------------------------
    def search(self, query: str, filters: Optional[Dict] = None, page: int = 1) -> List[NormalizedProduct]:
        """Búsqueda por texto → lista de NormalizedProduct (ligera). Ítems del
        listado que no normalicen se omiten (no rompen la búsqueda)."""
        data = self._get("search", "/productos", params={"busqueda": query, "pagina": page})
        items = data.get("productos") if isinstance(data, dict) else None
        out = []
        for it in (items or []):
            try:
                out.append(mapping.normalize(it))
            except NormalizationError:
                _logger.debug("ítem de listado omitido (incompleto)")
        return out

    def get_product(self, ref: str) -> NormalizedProduct:
        """Detalle completo y normalizado de un producto por su referencia Syscom.
        Lanza ConnectorError si Syscom lo reporta no disponible (payload {'error':...})."""
        raw = self._get("get_product", "/productos/%s" % ref)
        if mapping.is_error_payload(raw):
            raise ConnectorError("Producto %s no disponible: %s" % (ref, raw.get("error")))
        return mapping.normalize(raw)

    def get_price_stock(self, refs: List[str]) -> Dict[str, Dict]:
        """Precio/stock por ref. {ref: {price, stock}} o {ref: {error: True}}."""
        out: Dict[str, Dict] = {}
        for ref in refs:
            try:
                np = self.get_product(ref)
                out[ref] = {"price": vars(np.price), "stock": {"total": np.stock.total}}
            except ConnectorError:
                out[ref] = {"error": True}
        return out

    def normalize(self, raw: Dict) -> NormalizedProduct:
        """Mapea un payload crudo de Syscom a NormalizedProduct (delegado a lib.mapping)."""
        return mapping.normalize(raw)

    def quality_warnings(self, np: NormalizedProduct) -> List[str]:
        """Advertencias de calidad de datos para un producto normalizado (no detiene)."""
        return quality.check(np)
