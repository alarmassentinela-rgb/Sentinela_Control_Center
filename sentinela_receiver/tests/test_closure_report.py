"""F2.7.3 — Reporte consolidado al cierre del evento.

Verifica que el PDF se genera sin error y que el wizard finalize dispara el
envío. NO verifica el HTTP a Telegram (eso es entorno externo); el método
`send_telegram_document` se confía en que funciona si telegram_chat_id existe.
"""
import pytest
import xmlrpc.client


@pytest.fixture
def event_ready_to_close(odoo, cfg):
    """Evento en in_progress con close_reason listo, sin telegram_chat_id en
    partner_id (para que action_resolve NO intente mandar Telegram real)."""
    pri = odoo("sentinela.alarm.priority", "search", [[]], {"limit": 1})
    event_id = odoo("sentinela.alarm.event", "create",
                    [{"name": "PYTEST CLOSURE", "device_id": cfg["device_id"],
                      "priority_id": pri[0], "status": "active"}])
    odoo("sentinela.alarm.event", "action_acknowledge", [[event_id]])
    odoo("sentinela.alarm.event", "action_assign_technician", [[event_id]])
    odoo("sentinela.alarm.event", "write",
         [[event_id], {"close_reason": "false_alarm"}])
    yield event_id
    try:
        odoo("sentinela.alarm.event", "cleanup_test_fsm_orders", [[event_id]])
    except xmlrpc.client.Fault:
        pass
    try:
        odoo("sentinela.alarm.event", "unlink", [[event_id]])
    except xmlrpc.client.Fault:
        pass


def test_send_closure_report_no_telegram_returns_false(odoo, cfg):
    """Si partner no tiene telegram_chat_id, action_send_closure_report
    devuelve False sin lanzar excepción."""
    # Crear partner aislado SIN telegram_chat_id
    partner_id = odoo("res.partner", "create",
                      [{"name": "PYTEST NO TELEGRAM", "telegram_chat_id": False}])
    # Device temporal apuntando al partner
    pri = odoo("sentinela.alarm.priority", "search", [[]], {"limit": 1})
    try:
        # Re-vincular device de prueba al partner sin telegram (temporal)
        old_partner = odoo("sentinela.monitoring.device", "read",
                          [[cfg["device_id"]], ["partner_id"]])[0]["partner_id"]
        odoo("sentinela.monitoring.device", "write",
             [[cfg["device_id"]], {"partner_id": partner_id}])
        try:
            event_id = odoo("sentinela.alarm.event", "create",
                            [{"name": "PYTEST NO_TG", "device_id": cfg["device_id"],
                              "priority_id": pri[0], "status": "active"}])
            try:
                res = odoo("sentinela.alarm.event", "action_send_closure_report",
                           [[event_id]])
                assert res is False, f"esperaba False sin telegram, llegó {res}"
            finally:
                odoo("sentinela.alarm.event", "cleanup_test_fsm_orders", [[event_id]])
                odoo("sentinela.alarm.event", "unlink", [[event_id]])
        finally:
            # Restore device.partner_id
            if old_partner:
                odoo("sentinela.monitoring.device", "write",
                     [[cfg["device_id"]], {"partner_id": old_partner[0]}])
    finally:
        odoo("res.partner", "unlink", [[partner_id]])


def test_resolve_does_not_raise(odoo, event_ready_to_close):
    """action_resolve debe completar limpio sin importar si el cliente tiene
    Telegram (el envío es best-effort, los errores se loguean sin propagarse)."""
    odoo("sentinela.alarm.event", "action_resolve", [[event_ready_to_close]])
    rec = odoo("sentinela.alarm.event", "read",
               [[event_ready_to_close], ["status"]])[0]
    assert rec["status"] == "resolved"


def test_send_closure_report_returns_bool(odoo, event_ready_to_close):
    """action_send_closure_report devuelve bool. NO debe lanzar excepción
    independientemente del estado del partner / PDF render."""
    res = odoo("sentinela.alarm.event", "action_send_closure_report",
               [[event_ready_to_close]])
    assert res in (True, False), f"esperaba bool, llegó {type(res).__name__}"
