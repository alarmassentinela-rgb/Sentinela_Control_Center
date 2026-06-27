# -*- coding: utf-8 -*-
"""Sprint 1 — recursos de negocio del Portal (BFF).

Reenvía Mis Servicios + Facturación a Odoo `sentinela_api` usando la sesión efímera
del cliente (act-as): el aislamiento lo dan las record rules de Odoo (WS-2). El
Dashboard se AGREGA aquí en un único endpoint (`/v1/dashboard`) con caché TTL corto.
PDF/XML de CFDI también con caché. Todas las respuestas llevan meta de diagnóstico
(`server_time`, `request_id`; el Dashboard además `last_refresh`).

Solo lectura. Versionado bajo /v1 (sin cambios incompatibles).
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response

from .. import deps
from ..clock import utcnow
from ..services.cache import DASHBOARD_TTL_SEC, DOCUMENT_TTL_SEC, cache

router = APIRouter(prefix="/v1", tags=["portal"])

_SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}


def _server_time():
    return utcnow().isoformat() + "Z"


def _rid(request: Request):
    return getattr(request.state, "request_id", None) or request.headers.get("x-request-id") or "-"


def _meta(request: Request, **extra):
    return {"server_time": _server_time(), "request_id": _rid(request), **extra}


def _envelope(data, request: Request, **extra_meta):
    return {"data": data, "meta": _meta(request, **extra_meta)}


def _proxy(odoo, sess, path, request, params=None):
    """GET act-as a Odoo + envoltura {data, meta}. Mapea errores de sesión/recurso."""
    status, body = odoo.get_json_as(sess.odoo_session_id, path, params)
    if status == 200:
        return _envelope(body, request)
    if status in (301, 302, 303, 401):
        raise HTTPException(status_code=401, detail="session_expired")
    if status == 404:
        detail = (body.get("title") if isinstance(body, dict) else None) or "not_found"
        raise HTTPException(status_code=404, detail=detail)
    raise HTTPException(status_code=502, detail="odoo_unavailable")


# ---------------- Config / branding (público) ----------------
_THEME_FALLBACK = {
    "app_name": "Sentinela", "logo_url": "", "primary_color": "#0B5FFF",
    "support_phone": "", "support_whatsapp": "",
}


@router.get("/config/theme", summary="Branding del portal (público)")
def config_theme(odoo=Depends(deps.get_odoo_client)):
    # Endpoint público de Odoo (no requiere sesión). Cache corto + fallback de marca.
    hit = cache.get("theme")
    if hit:
        return hit[0]
    status, body = odoo.get_json_as("", "/v1/config/theme")
    theme = body if (status == 200 and isinstance(body, dict)) else _THEME_FALLBACK
    cache.set("theme", theme, DASHBOARD_TTL_SEC)
    return theme


# ---------------- Perfil ----------------
@router.get("/me", summary="Perfil del cliente autenticado")
def me(request: Request, sess=Depends(deps.current_session), odoo=Depends(deps.get_odoo_client)):
    # Proxy del /v1/me de Odoo (sentinela_api) vía la sesión efímera. Respuesta cruda
    # (no envuelta) para coincidir con el contrato OpenAPI existente.
    status, body = odoo.get_json_as(sess.odoo_session_id, "/v1/me")
    if status == 200:
        return body
    if status in (301, 302, 303, 401):
        raise HTTPException(status_code=401, detail="session_expired")
    raise HTTPException(status_code=502, detail="odoo_unavailable")


# ---------------- Mis Servicios ----------------
@router.get("/services", summary="Lista de servicios del cliente")
def services(request: Request, sess=Depends(deps.current_session), odoo=Depends(deps.get_odoo_client)):
    return _proxy(odoo, sess, "/v1/services", request)


@router.get("/services/{service_id}", summary="Detalle de un servicio")
def service_detail(service_id: int, request: Request,
                   sess=Depends(deps.current_session), odoo=Depends(deps.get_odoo_client)):
    return _proxy(odoo, sess, f"/v1/services/{service_id}", request)


# ---------------- Facturación (consulta) ----------------
@router.get("/billing/summary", summary="Estado de cuenta (resumen)")
def billing_summary(request: Request, sess=Depends(deps.current_session), odoo=Depends(deps.get_odoo_client)):
    return _proxy(odoo, sess, "/v1/billing/summary", request)


@router.get("/billing/invoices", summary="Lista de facturas/remisiones")
def billing_invoices(request: Request, page: int = 1, limit: int = 20,
                     sess=Depends(deps.current_session), odoo=Depends(deps.get_odoo_client)):
    return _proxy(odoo, sess, "/v1/billing/invoices", request, params={"page": page, "limit": limit})


@router.get("/billing/invoices/{invoice_id}", summary="Detalle de una factura")
def billing_invoice_detail(invoice_id: int, request: Request,
                           sess=Depends(deps.current_session), odoo=Depends(deps.get_odoo_client)):
    return _proxy(odoo, sess, f"/v1/billing/invoices/{invoice_id}", request)


@router.get("/billing/payments", summary="Historial de pagos")
def billing_payments(request: Request, page: int = 1, limit: int = 20,
                     sess=Depends(deps.current_session), odoo=Depends(deps.get_odoo_client)):
    return _proxy(odoo, sess, "/v1/billing/payments", request, params={"page": page, "limit": limit})


def _document(request, sess, odoo, invoice_id, kind, default_ctype):
    key = f"{kind}:{sess.partner_id}:{invoice_id}"
    hit = cache.get(key)
    if hit:
        (content, ctype, cdisp), _ = hit
    else:
        status, content, ctype, cdisp = odoo.get_raw_as(
            sess.odoo_session_id, f"/v1/billing/invoices/{invoice_id}/{kind}")
        if status in (301, 302, 303, 401):
            raise HTTPException(status_code=401, detail="session_expired")
        if status == 404:
            raise HTTPException(status_code=404, detail="not_found")
        if status != 200 or not content:
            raise HTTPException(status_code=502, detail="odoo_unavailable")
        cache.set(key, (content, ctype, cdisp), DOCUMENT_TTL_SEC)
    headers = {"X-Request-Id": _rid(request)}
    if cdisp:
        headers["Content-Disposition"] = cdisp
    return Response(content=content, media_type=ctype or default_ctype, headers=headers)


@router.get("/billing/invoices/{invoice_id}/pdf", summary="PDF de la factura (CFDI)")
def billing_invoice_pdf(invoice_id: int, request: Request,
                        sess=Depends(deps.current_session), odoo=Depends(deps.get_odoo_client)):
    return _document(request, sess, odoo, invoice_id, "pdf", "application/pdf")


@router.get("/billing/invoices/{invoice_id}/xml", summary="XML del CFDI")
def billing_invoice_xml(invoice_id: int, request: Request,
                        sess=Depends(deps.current_session), odoo=Depends(deps.get_odoo_client)):
    return _document(request, sess, odoo, invoice_id, "xml", "application/xml")


# ---------------- Dashboard (agregado, cache 30s) ----------------
def _money(v):
    try:
        return f"${float(v):,.2f}"
    except (TypeError, ValueError):
        return None


def _build_dashboard(services_body, billing_body):
    items = services_body.get("items", []) if isinstance(services_body, dict) else []
    billing = billing_body if isinstance(billing_body, dict) else {}
    total = len(items)
    active = sum(1 for s in items if s.get("status") == "active")
    suspended = sum(1 for s in items if s.get("status") == "suspended")
    pending_sign = [s for s in items if s.get("status") == "pending_signature"]
    total_due = billing.get("total_due", 0) or 0
    overdue = billing.get("overdue_amount", 0) or 0
    upcoming = billing.get("upcoming", []) or []

    # Estado de Tranquilidad — agregación SIMPLE en esta etapa (decisión aprobada).
    # Se enriquecerá cuando entren Alarmas/Internet/GPS en sprints posteriores.
    if suspended > 0 or overdue > 0:
        overall, label = "atencion", "Requiere tu atención"
    else:
        overall, label = "tranquilo", "Todo en orden"

    actions = []
    if overdue > 0:
        actions.append({"key": "pago_vencido", "type": "payment_overdue", "severity": "high",
                        "title": "Tienes un saldo vencido", "detail": "Adeudo vencido por %s" % _money(overdue),
                        "amount": overdue, "target": "/facturacion"})
    for inv in upcoming:
        if (inv.get("amount_due") or 0) > 0:
            actions.append({"key": "factura_%s" % inv.get("id"), "type": "invoice_due", "severity": "medium",
                            "title": "Factura %s por pagar" % (inv.get("number") or ""),
                            "detail": "Vence %s · %s" % (inv.get("due_date") or "s/f", _money(inv.get("amount_due"))),
                            "amount": inv.get("amount_due"), "target": "/facturacion/%s" % inv.get("id")})
    for s in pending_sign:
        actions.append({"key": "firma_%s" % s.get("id"), "type": "contract_pending_signature", "severity": "medium",
                        "title": "Contrato por firmar", "detail": s.get("plan") or s.get("reference") or "",
                        "target": "/servicios/%s" % s.get("id")})
    for s in items:
        if s.get("status") == "suspended":
            actions.append({"key": "susp_%s" % s.get("id"), "type": "service_suspended", "severity": "high",
                            "title": "Servicio suspendido",
                            "detail": "%s — %s" % (s.get("service_type_label") or "", s.get("reference") or ""),
                            "target": "/servicios/%s" % s.get("id")})
    actions.sort(key=lambda a: _SEVERITY_RANK.get(a["severity"], 9))

    return {
        "peace_of_mind": {"status": overall, "label": label},
        "services": {
            "total": total, "active": active, "suspended": suspended,
            "items": [{"id": s.get("id"), "reference": s.get("reference"),
                       "service_type": s.get("service_type"), "service_type_label": s.get("service_type_label"),
                       "status": s.get("status"), "plan": s.get("plan")} for s in items],
        },
        "billing": {
            "total_due": total_due, "overdue_amount": overdue,
            "currency": billing.get("currency", "MXN"), "upcoming": upcoming,
        },
        "next_actions": actions,
    }


@router.get("/dashboard", summary="Dashboard agregado (un solo endpoint, cache 30s)")
def dashboard(request: Request, sess=Depends(deps.current_session), odoo=Depends(deps.get_odoo_client)):
    key = "dash:%s" % sess.partner_id
    hit = cache.get(key)
    if hit:
        payload, created = hit
        last_refresh = created.isoformat() + "Z"
    else:
        s_st, services_body = odoo.get_json_as(sess.odoo_session_id, "/v1/services")
        b_st, billing_body = odoo.get_json_as(sess.odoo_session_id, "/v1/billing/summary")
        if s_st in (301, 302, 303, 401) or b_st in (301, 302, 303, 401):
            raise HTTPException(status_code=401, detail="session_expired")
        if s_st != 200 or b_st != 200:
            raise HTTPException(status_code=502, detail="odoo_unavailable")
        payload = _build_dashboard(services_body, billing_body)
        cache.set(key, payload, DASHBOARD_TTL_SEC)
        # last_refresh = momento real de cómputo (el created_at que guardó el caché),
        # para que coincida en hits posteriores dentro del TTL.
        stored = cache.get(key)
        last_refresh = (stored[1].isoformat() + "Z") if stored else _server_time()
    return _envelope(payload, request, last_refresh=last_refresh, cache_ttl_sec=DASHBOARD_TTL_SEC)
