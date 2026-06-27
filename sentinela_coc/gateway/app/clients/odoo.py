# -*- coding: utf-8 -*-
"""Cliente desacoplado de Odoo (handshake de sesión efímera, W5.6).

Interfaz + implementación HTTP real + Fake para pruebas (sin Odoo).
El aislamiento lo aplica Odoo (record rules); este cliente solo abre/cierra la
sesión efímera del usuario portal y resuelve teléfono->partner.
"""
from abc import ABC, abstractmethod

import httpx


class OdooClient(ABC):
    @abstractmethod
    def resolve_phone(self, phone: str) -> int | None:
        ...

    @abstractmethod
    def open_session(self, partner_id: int, ttl_seconds: int, device: str | None,
                     ip: str | None, user_agent: str | None) -> dict:
        ...

    @abstractmethod
    def close_session(self, odoo_session_id: str) -> dict:
        ...

    @abstractmethod
    def set_phone(self, partner_id: int, phone: str) -> dict:
        ...

    # --- Sprint 1: recursos de negocio "act-as" (la peticion corre como el
    #     usuario portal usando SU sesion efimera; el aislamiento lo dan las
    #     record rules de Odoo, igual que en WS-2). ---
    @abstractmethod
    def get_json_as(self, odoo_session_id: str, path: str, params: dict | None = None) -> tuple[int, object]:
        ...

    @abstractmethod
    def get_raw_as(self, odoo_session_id: str, path: str) -> tuple[int, bytes, str | None, str | None]:
        ...


class HttpOdooClient(OdooClient):
    def __init__(self, base_url: str, shared_secret: str):
        self.base_url = base_url.rstrip("/")
        self.secret = shared_secret

    def _call(self, path: str, params: dict) -> dict:
        url = f"{self.base_url}{path}"
        payload = {"jsonrpc": "2.0", "method": "call", "params": params}
        r = httpx.post(url, json=payload, headers={"X-COC-Secret": self.secret}, timeout=10)
        r.raise_for_status()
        return (r.json() or {}).get("result", {})

    def resolve_phone(self, phone: str) -> int | None:
        res = self._call("/coc/internal/identity/resolve", {"phone": phone})
        return res.get("partner_id") if res.get("ok") else None

    def open_session(self, partner_id, ttl_seconds, device, ip, user_agent) -> dict:
        return self._call("/coc/internal/session/open", {
            "partner_id": partner_id, "ttl_seconds": ttl_seconds, "device": device,
        })

    def close_session(self, odoo_session_id: str) -> dict:
        return self._call("/coc/internal/session/close", {"session_id": odoo_session_id})

    def set_phone(self, partner_id: int, phone: str) -> dict:
        return self._call("/coc/internal/identity/set_phone", {"partner_id": partner_id, "phone": phone})

    def get_json_as(self, odoo_session_id, path, params=None):
        r = httpx.get(f"{self.base_url}{path}", params=params or {},
                      cookies={"session_id": odoo_session_id}, timeout=20, follow_redirects=False)
        try:
            body = r.json()
        except Exception:
            body = None
        return r.status_code, body

    def get_raw_as(self, odoo_session_id, path):
        r = httpx.get(f"{self.base_url}{path}", cookies={"session_id": odoo_session_id},
                      timeout=30, follow_redirects=False)
        return (r.status_code, r.content,
                r.headers.get("content-type"), r.headers.get("content-disposition"))


class FakeOdooClient(OdooClient):
    """Para pruebas: mapea teléfonos a partners y simula sesiones efímeras."""
    def __init__(self, phone_map: dict[str, int] | None = None):
        self.phone_map = phone_map or {}
        self._seq = 0
        self.open_sessions: set[str] = set()
        # Respuestas de negocio canned para pruebas: path -> (status, body) / (status, bytes, ctype, cdisp)
        self.json_responses: dict[str, tuple] = {}
        self.raw_responses: dict[str, tuple] = {}

    def resolve_phone(self, phone: str) -> int | None:
        return self.phone_map.get(phone)

    def open_session(self, partner_id, ttl_seconds, device, ip, user_agent) -> dict:
        self._seq += 1
        sid = f"fake-odoo-sess-{self._seq}"
        self.open_sessions.add(sid)
        return {"ok": True, "session_id": sid, "uid": 1000 + partner_id, "expires_at": None}

    def close_session(self, odoo_session_id: str) -> dict:
        self.open_sessions.discard(odoo_session_id)
        return {"ok": True}

    def set_phone(self, partner_id: int, phone: str) -> dict:
        # refleja el cambio en el mapa teléfono->partner
        self.phone_map = {p: pid for p, pid in self.phone_map.items() if pid != partner_id}
        self.phone_map[phone] = partner_id
        return {"ok": True}

    def get_json_as(self, odoo_session_id, path, params=None):
        return self.json_responses.get(path, (404, {"title": "not_found", "status": 404}))

    def get_raw_as(self, odoo_session_id, path):
        return self.raw_responses.get(path, (404, b"", None, None))
