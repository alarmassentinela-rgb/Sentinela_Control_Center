"""F2.6 Cobranza al atender — autorización + creación de sale.order automática."""
import pytest


@pytest.fixture
def patrol_product(odoo):
    """Crea un producto-servicio para usar como patrol_service_product_id.
    Configura el ir.config_parameter y lo deja seteado durante el test."""
    existing = odoo("product.product", "search",
                    [[("default_code", "=", "PYTEST_PATROL")]])
    if existing:
        prod_id = existing[0]
    else:
        prod_id = odoo("product.product", "create",
                       [{"name": "Servicio Patrulla (test)",
                         "default_code": "PYTEST_PATROL",
                         "type": "service",
                         "list_price": 500.0}])
    # Guardar valor previo del config_parameter
    prev = odoo("ir.config_parameter", "search_read",
                [[("key", "=", "sentinela_monitoring.patrol_service_product_id")],
                 ["value"]])
    prev_val = prev[0]["value"] if prev else False
    odoo("ir.config_parameter", "set_param",
         ["sentinela_monitoring.patrol_service_product_id", str(prod_id)])
    yield prod_id
    # Restore
    if prev_val:
        odoo("ir.config_parameter", "set_param",
             ["sentinela_monitoring.patrol_service_product_id", prev_val])
    else:
        odoo("ir.config_parameter", "set_param",
             ["sentinela_monitoring.patrol_service_product_id", ""])


@pytest.fixture
def event_for_billing(odoo, cfg):
    pri = odoo("sentinela.alarm.priority", "search", [[]], {"limit": 1})
    event_id = odoo("sentinela.alarm.event", "create",
                    [{"name": "PYTEST BILLING", "device_id": cfg["device_id"],
                      "priority_id": pri[0], "status": "active"}])
    yield event_id
    # Desligar sale_order_id antes del unlink — el cleanup de la venta lo
    # hace cualquiera con permisos, no nos preocupa aquí.
    odoo("sentinela.alarm.event", "write",
         [[event_id], {"sale_order_id": False}])
    odoo("sentinela.alarm.event", "unlink", [[event_id]])


def test_request_authorization_sets_strategy(odoo, event_for_billing):
    odoo("sentinela.alarm.event", "action_request_service_authorization",
         [[event_for_billing], "patrol", "telegram"])
    rec = odoo("sentinela.alarm.event", "read",
               [[event_for_billing],
                ["patrol_strategy", "authorization_method",
                 "extra_service_authorized", "sale_order_id"]])[0]
    assert rec["patrol_strategy"] == "request_auth"
    assert rec["authorization_method"] == "telegram"
    assert rec["extra_service_authorized"] is False
    assert rec["sale_order_id"] is False, "request NO debe crear venta todavía"


def test_authorize_service_creates_sale_order(odoo, event_for_billing, patrol_product):
    odoo("sentinela.alarm.event", "action_authorize_service",
         [[event_for_billing]])
    rec = odoo("sentinela.alarm.event", "read",
               [[event_for_billing],
                ["extra_service_authorized", "sale_order_id", "partner_id"]])[0]
    assert rec["extra_service_authorized"] is True
    assert rec["sale_order_id"], "authorize_service debe crear sale.order"
    # Usar helper sudo del modelo para evitar permisos de sale.order
    info = odoo("sentinela.alarm.event", "get_sale_order_info", [[event_for_billing]])
    assert info["partner_id"] == rec["partner_id"][0]
    assert "PYTEST BILLING" in (info["origin"] or "")
    assert len(info["lines"]) == 1
    assert info["lines"][0]["product_id"] == patrol_product
    assert info["lines"][0]["qty"] == 1.0


def test_authorize_idempotent_does_not_duplicate(odoo, event_for_billing, patrol_product):
    """Llamar authorize dos veces NO debe crear una segunda sale.order."""
    odoo("sentinela.alarm.event", "action_authorize_service", [[event_for_billing]])
    first = odoo("sentinela.alarm.event", "read",
                 [[event_for_billing], ["sale_order_id"]])[0]["sale_order_id"]
    odoo("sentinela.alarm.event", "action_authorize_service", [[event_for_billing]])
    second = odoo("sentinela.alarm.event", "read",
                  [[event_for_billing], ["sale_order_id"]])[0]["sale_order_id"]
    assert first == second, f"authorize duplicó la venta: {first} → {second}"


def test_no_sale_order_when_product_not_configured(odoo, event_for_billing):
    """Sin patrol_service_product_id configurado, authorize marca flag pero no crea venta."""
    # Borrar config explícitamente
    odoo("ir.config_parameter", "set_param",
         ["sentinela_monitoring.patrol_service_product_id", ""])
    odoo("sentinela.alarm.event", "action_authorize_service", [[event_for_billing]])
    rec = odoo("sentinela.alarm.event", "read",
               [[event_for_billing], ["extra_service_authorized", "sale_order_id"]])[0]
    assert rec["extra_service_authorized"] is True
    assert rec["sale_order_id"] is False, "sin producto configurado NO debe crear venta"
