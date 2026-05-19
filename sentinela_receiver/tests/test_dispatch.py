"""F2.7.2 — Despacho de patrulla: create_fsm_order + lógica condicional por plan."""
import pytest
import xmlrpc.client


@pytest.fixture
def event_with_partner(odoo, cfg):
    """Evento con device y partner. Limpia fsm.order al final."""
    pri = odoo("sentinela.alarm.priority", "search", [[]], {"limit": 1})
    event_id = odoo("sentinela.alarm.event", "create",
                    [{"name": "PYTEST DISPATCH", "device_id": cfg["device_id"],
                      "priority_id": pri[0], "status": "active"}])
    yield event_id
    # Cleanup fsm.orders linkadas (best-effort, api_user no tiene permisos)
    try:
        infos = odoo("sentinela.alarm.event", "get_fsm_orders_info", [[event_id]])
        # Si tenemos info, no podemos delete (sin permisos) — desligar campo
        # Realmente delete vía un helper sudo:
        if infos:
            odoo("sentinela.alarm.event", "cleanup_test_fsm_orders", [[event_id]])
    except xmlrpc.client.Fault:
        pass
    try:
        odoo("sentinela.alarm.event", "unlink", [[event_id]])
    except xmlrpc.client.Fault:
        pass


def test_create_fsm_order_creates_patrol_task(odoo, cfg, event_with_partner):
    """alarm_event.create_fsm_order crea sentinela.fsm.order vinculada."""
    technician = odoo("res.users", "search", [[]], {"limit": 1})
    fsm_id = odoo("sentinela.alarm.event", "create_fsm_order",
                  [[event_with_partner], technician[0], 'patrol'])
    assert fsm_id, "create_fsm_order debe devolver el id de la orden"
    infos = odoo("sentinela.alarm.event", "get_fsm_orders_info",
                 [[event_with_partner]])
    assert len(infos) == 1
    info = infos[0]
    assert info["service_type"] == "patrol"
    assert info["technician_id"] == technician[0]
    assert info["stage"] == "assigned"


def test_create_fsm_order_is_idempotent(odoo, cfg, event_with_partner):
    """Llamar create_fsm_order 2 veces NO duplica — devuelve la existente."""
    technician = odoo("res.users", "search", [[]], {"limit": 1})
    first = odoo("sentinela.alarm.event", "create_fsm_order",
                 [[event_with_partner], technician[0], 'patrol'])
    second = odoo("sentinela.alarm.event", "create_fsm_order",
                  [[event_with_partner], technician[0], 'patrol'])
    assert first == second, f"esperaba misma orden, llegó {first} → {second}"
    infos = odoo("sentinela.alarm.event", "get_fsm_orders_info",
                 [[event_with_partner]])
    assert len(infos) == 1, "no debe haber duplicados"


def test_event_status_becomes_in_progress(odoo, event_with_partner):
    """create_fsm_order también pasa el evento a status='in_progress'."""
    technician = odoo("res.users", "search", [[]], {"limit": 1})
    odoo("sentinela.alarm.event", "create_fsm_order",
         [[event_with_partner], technician[0], 'patrol'])
    rec = odoo("sentinela.alarm.event", "read",
               [[event_with_partner], ["status"]])[0]
    assert rec["status"] == "in_progress"


def test_close_reason_includes_cliente_rechazo(odoo):
    """Verifica que cliente_rechazo_servicio existe en el Selection."""
    pri = odoo("sentinela.alarm.priority", "search", [[]], {"limit": 1})
    cfg_device = 4  # fallback
    event_id = odoo("sentinela.alarm.event", "create",
                    [{"name": "PYTEST RECHAZO", "device_id": cfg_device,
                      "priority_id": pri[0], "status": "active"}])
    try:
        odoo("sentinela.alarm.event", "action_acknowledge", [[event_id]])
        odoo("sentinela.alarm.event", "action_assign_technician", [[event_id]])
        # Probar que cliente_rechazo_servicio es válido en el Selection
        odoo("sentinela.alarm.event", "write",
             [[event_id], {"close_reason": "cliente_rechazo_servicio"}])
        odoo("sentinela.alarm.event", "action_resolve", [[event_id]])
        rec = odoo("sentinela.alarm.event", "read",
                   [[event_id], ["status", "close_reason"]])[0]
        assert rec["status"] == "resolved"
        assert rec["close_reason"] == "cliente_rechazo_servicio"
    finally:
        odoo("sentinela.alarm.event", "unlink", [[event_id]])
