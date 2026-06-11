"""Odoo XML-RPC integration — capa reusada del bot OpenClaw (verbatim) + helper
de orden "POR CONCILIAR" para reportes sin match de teléfono.

Lee la conexión de variables de entorno: ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD.
"""

import logging
import xmlrpc.client
from functools import lru_cache

logger = logging.getLogger("chatwoot_bot.odoo")

_ODOO_URL = None
_ODOO_DB = None
_ODOO_USER = None
_ODOO_PASSWORD = None
_ODOO_UID = None


def _init():
    global _ODOO_URL, _ODOO_DB, _ODOO_USER, _ODOO_PASSWORD
    import os
    _ODOO_URL = os.environ.get("ODOO_URL", "")
    _ODOO_DB = os.environ.get("ODOO_DB", "")
    _ODOO_USER = os.environ.get("ODOO_USER", "")
    _ODOO_PASSWORD = os.environ.get("ODOO_PASSWORD", "")


def _get_uid() -> int | None:
    global _ODOO_UID
    if _ODOO_UID:
        return _ODOO_UID
    if not _ODOO_URL:
        _init()
    if not all([_ODOO_URL, _ODOO_DB, _ODOO_USER, _ODOO_PASSWORD]):
        return None
    try:
        common = xmlrpc.client.ServerProxy(f"{_ODOO_URL}/xmlrpc/2/common", allow_none=True)
        _ODOO_UID = common.authenticate(_ODOO_DB, _ODOO_USER, _ODOO_PASSWORD, {})
        return _ODOO_UID if _ODOO_UID else None
    except Exception as e:
        logger.error("Odoo auth error: %s", e)
        return None


def _models():
    if not _ODOO_URL:
        _init()
    return xmlrpc.client.ServerProxy(f"{_ODOO_URL}/xmlrpc/2/object", allow_none=True)


def _call(model: str, method: str, args: list, kwargs: dict = None) -> any:
    uid = _get_uid()
    if not uid:
        return None
    try:
        return _models().execute_kw(
            _ODOO_DB, uid, _ODOO_PASSWORD,
            model, method, args, kwargs or {}
        )
    except Exception as e:
        logger.error("Odoo call %s.%s error: %s", model, method, e)
        return None


# ── Búsqueda de cliente por teléfono ──────────────────────────────

def find_partner_by_phone(phone: str) -> dict | None:
    """Busca un res.partner por número de teléfono.
    
    Maneja formatos: +52 868 840 6808, 8688406808, 528688406808
    """
    digits = "".join(c for c in phone if c.isdigit())
    if not digits:
        return None

    # Tomar los últimos 10 dígitos (número local con área)
    local = digits[-10:] if len(digits) >= 10 else digits
    # Partir en 3 segmentos con % entre ellos para tolerar espacios/guiones en la DB
    # Ej: 8688406808 → '868%840%6808' → coincide con '+52 868 840 6808'
    if len(local) >= 10:
        pattern = f"{local[0:3]}%{local[3:6]}%{local[6:]}"
    elif len(local) >= 7:
        pattern = f"{local[:3]}%{local[3:]}"
    else:
        pattern = local

    domain = ["|",
        ("phone", "like", pattern),
        ("mobile", "like", pattern),
    ]
    results = _call("res.partner", "search_read", [domain], {
        "fields": ["id", "name", "phone", "mobile", "email"],
        "limit": 1
    })
    if results:
        return results[0]

    # Fallback: últimos 8 dígitos sin partir
    key8 = digits[-8:]
    domain2 = ["|",
        ("phone", "like", key8),
        ("mobile", "like", key8),
    ]
    results = _call("res.partner", "search_read", [domain2], {
        "fields": ["id", "name", "phone", "mobile", "email"],
        "limit": 1
    })
    return results[0] if results else None


# ── Suscripciones ─────────────────────────────────────────────────

def get_subscriptions(partner_id: int) -> list[dict]:
    """Retorna suscripciones activas/suspendidas del cliente."""
    results = _call("sentinela.subscription", "search_read",
        [[("partner_id", "=", partner_id), ("state", "in", ["active", "suspension", "confirmed"])]],
        {"fields": ["name", "state", "service_type", "product_id",
                    "price_unit", "next_billing_date", "technical_state",
                    "pppoe_user", "ip_address", "extension_due_date"],
         "order": "state asc"}
    )
    return results or []


# ── Facturas pendientes ───────────────────────────────────────────

def get_pending_invoices(partner_id: int) -> list[dict]:
    """Retorna facturas sin pagar del cliente."""
    results = _call("account.move", "search_read",
        [[("partner_id", "=", partner_id),
          ("move_type", "=", "out_invoice"),
          ("payment_state", "in", ["not_paid", "partial"]),
          ("state", "=", "posted")]],
        {"fields": ["name", "invoice_date_due", "amount_total",
                    "amount_residual", "payment_state"],
         "order": "invoice_date_due asc"}
    )
    return results or []


# ── Crear orden FSM ───────────────────────────────────────────────

def get_single_active_subscription_id(partner_id: int) -> int | None:
    """Devuelve el id de la suscripción activa del cliente SOLO si tiene
    exactamente una (para ligar el ticket sin ambigüedad). Si tiene varias
    o ninguna, retorna None y el coordinador la elige al agendar."""
    subs = _call("sentinela.subscription", "search_read",
        [[("partner_id", "=", partner_id), ("state", "in", ["active", "suspension", "confirmed"])]],
        {"fields": ["id"], "limit": 2}
    )
    if subs and len(subs) == 1:
        return subs[0]["id"]
    return None


def create_fsm_order(partner_id: int, description: str,
                     service_type: str = "repair",
                     subscription_id: int | None = None) -> dict | None:
    """Crea una Orden de Servicio real (sentinela.fsm.order) en etapa 'Nuevo'.

    El coordinador la verá en el tablero y agendará técnico + fecha.
    Devuelve {'id', 'name' (folio), 'ok'}.
    """
    vals = {
        "partner_id": partner_id,
        "description": description,
        "service_type": service_type,
        "priority": "0",
    }
    if subscription_id:
        vals["subscription_id"] = subscription_id

    new_id = _call("sentinela.fsm.order", "create", [vals])
    if not new_id:
        return None
    rec = _call("sentinela.fsm.order", "read", [new_id], {"fields": ["name"]})
    folio = rec[0]["name"] if rec else str(new_id)
    return {"id": new_id, "name": folio, "ok": True}


# ── Orden "POR CONCILIAR" (reporte sin match de teléfono) ─────────

_RECONCILE_PARTNER_REF = "chatwoot_bot.partner_por_conciliar"
_RECONCILE_PARTNER_NAME = "⚠ POR CONCILIAR (Reportes Web)"


@lru_cache(maxsize=1)
def get_reconcile_partner_id() -> int | None:
    """Partner placeholder único al que se ligan los reportes sin cuenta
    identificada (partner_id es obligatorio en la orden). Recepción re-vincula
    la orden al cliente real. Se busca/crea por nombre para no duplicar."""
    found = _call("res.partner", "search_read",
        [[("name", "=", _RECONCILE_PARTNER_NAME)]],
        {"fields": ["id"], "limit": 1})
    if found:
        return found[0]["id"]
    new_id = _call("res.partner", "create", [{
        "name": _RECONCILE_PARTNER_NAME,
        "is_company": True,
        "comment": "Cuenta técnica: reportes entrantes por WhatsApp sin teléfono "
                   "identificado. Recepción debe reasignar la orden al cliente real.",
    }])
    return new_id or None


def create_reconcile_fsm_order(phone: str, description: str,
                               contact_name: str = "") -> dict | None:
    """Crea la orden de un reporte cuyo teléfono NO matchea ningún cliente.
    La liga al partner placeholder y deja el teléfono/nombre capturados en la
    descripción para que recepción la concilie. NO se pierde el reporte."""
    pid = get_reconcile_partner_id()
    if not pid:
        return None
    header = "[POR CONCILIAR] Reporte por WhatsApp sin cuenta identificada.\n"
    if contact_name:
        header += f"Nombre WhatsApp: {contact_name}\n"
    header += f"Teléfono: {phone}\n---\n"
    res = create_fsm_order(pid, header + (description or ""), service_type="repair")
    return res


# ── Búsqueda por nombre (uso administrativo) ─────────────────────

def search_partners_by_name(name: str, limit: int = 5) -> list[dict]:
    """Busca clientes por nombre (búsqueda parcial)."""
    results = _call("res.partner", "search_read",
        [[("name", "ilike", name), ("is_company", "=", False)]],
        {"fields": ["id", "name", "phone", "mobile", "email"], "limit": limit, "order": "name asc"}
    )
    return results or []


def get_all_subscriptions(partner_id: int) -> list[dict]:
    """Retorna TODAS las suscripciones de un cliente (incluyendo canceladas/cerradas)."""
    results = _call("sentinela.subscription", "search_read",
        [[("partner_id", "=", partner_id)]],
        {"fields": ["name", "state", "service_type", "product_id", "price_unit",
                    "next_billing_date", "technical_state", "start_date",
                    "pppoe_user", "ip_address", "extension_due_date"],
         "order": "state asc, start_date desc"}
    )
    return results or []


def get_admin_client_summary(name_or_phone: str) -> str:
    """
    Resumen completo de un cliente para uso administrativo.
    Acepta nombre parcial o número de teléfono.
    """
    partners = []

    # Intentar primero como teléfono
    digits = "".join(c for c in name_or_phone if c.isdigit())
    if len(digits) >= 7:
        p = find_partner_by_phone(digits)
        if p:
            partners = [p]

    # Si no encontró por teléfono, buscar por nombre
    if not partners:
        partners = search_partners_by_name(name_or_phone, limit=3)

    if not partners:
        return f"No se encontró ningún cliente con '{name_or_phone}' en el sistema."

    lines = []
    for partner in partners:
        lines.append(f"\n{'='*40}")
        lines.append(f"CLIENTE: {partner['name']}")
        if partner.get('phone'):
            lines.append(f"Tel: {partner['phone']}")
        if partner.get('mobile'):
            lines.append(f"Cel: {partner['mobile']}")
        if partner.get('email'):
            lines.append(f"Email: {partner['email']}")

        subs = get_all_subscriptions(partner["id"])
        if subs:
            lines.append(f"\nSUSCRIPCIONES ({len(subs)}):")
            state_map = {"active": "✅ Activo", "suspension": "⏸ Suspendido",
                         "confirmed": "🔵 Por activar", "draft": "📝 Borrador",
                         "cancelled": "❌ Cancelado", "closed": "🔒 Cerrado"}
            type_map = {"internet": "🌐 Internet", "alarm": "🔔 Monitoreo",
                        "gps": "📍 GPS", "maintenance": "🔧 Mantenimiento"}
            for s in subs:
                estado = state_map.get(s.get("state", ""), s.get("state", ""))
                tipo = type_map.get(s.get("service_type", ""), s.get("service_type", ""))
                plan = s.get("product_id", [None, ""])[1] if s.get("product_id") else "Sin plan"
                precio = s.get("price_unit", 0)
                prox = s.get("next_billing_date", "—")
                lines.append(f"  {s['name']} | {tipo} | {plan} | ${precio:.0f}/mes | {estado} | Cobro: {prox}")
                if s.get("pppoe_user"):
                    lines.append(f"    PPPoE: {s['pppoe_user']} | IP: {s.get('ip_address') or 'N/A'}")
        else:
            lines.append("Sin suscripciones registradas.")

        invoices = get_pending_invoices(partner["id"])
        if invoices:
            total = sum(i.get("amount_residual", 0) for i in invoices)
            lines.append(f"\nADEUDO: ${total:.2f} MXN ({len(invoices)} factura(s))")
            for inv in invoices:
                lines.append(f"  {inv['name']} | ${inv['amount_residual']:.2f} | Vence: {inv.get('invoice_date_due', 'N/A')}")
        else:
            lines.append("\nADEUDO: Al corriente ✅")

    if len(partners) > 1:
        lines.insert(0, f"Se encontraron {len(partners)} clientes con '{name_or_phone}':")

    return "\n".join(lines)


# ── Resumen de cliente ────────────────────────────────────────────

def get_client_summary(phone: str) -> str:
    """
    Genera un bloque de contexto para inyectar al system prompt.
    Retorna string vacío si no se encuentra el cliente.
    """
    partner = find_partner_by_phone(phone)
    if not partner:
        return ""

    lines = [f"CLIENTE EN ODOO: {partner['name']}"]

    subs = get_subscriptions(partner["id"])
    if subs:
        for s in subs:
            state_map = {
                "active": "Activo", "suspension": "Suspendido",
                "confirmed": "Por activar", "draft": "Borrador"
            }
            type_map = {
                "internet": "Internet", "alarm": "Monitoreo",
                "gps": "GPS", "maintenance": "Mantenimiento"
            }
            estado = state_map.get(s.get("state", ""), s.get("state", ""))
            tipo = type_map.get(s.get("service_type", ""), s.get("service_type", ""))
            plan = s.get("product_id", [None, ""])[1] if s.get("product_id") else ""
            precio = s.get("price_unit", 0)
            prox_cobro = s.get("next_billing_date", "")
            tech = s.get("technical_state", "")

            sub_line = f"- Suscripción {s['name']} | {tipo} | {plan} | ${precio:.0f}/mes | Estado: {estado}"
            if tech == "suspended":
                sub_line += " ⚠️ Línea técnica suspendida"
            if prox_cobro:
                sub_line += f" | Próximo cobro: {prox_cobro}"
            if s.get("extension_due_date"):
                sub_line += f" | Prórroga hasta: {s['extension_due_date']}"
            lines.append(sub_line)
    else:
        lines.append("- Sin suscripciones activas en el sistema")

    invoices = get_pending_invoices(partner["id"])
    if invoices:
        total_due = sum(i.get("amount_residual", 0) for i in invoices)
        lines.append(f"ADEUDO: ${total_due:.2f} MXN ({len(invoices)} factura(s) pendiente(s))")
        for inv in invoices[:3]:
            lines.append(f"  - {inv['name']} | ${inv['amount_residual']:.2f} | Vence: {inv.get('invoice_date_due', 'N/A')}")
    else:
        lines.append("ADEUDO: Al corriente (sin facturas pendientes)")

    return "\n".join(lines)
