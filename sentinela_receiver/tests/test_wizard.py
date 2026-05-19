"""F2.4 Wizard guiado: stepper, auto-acknowledge al abrir, atajos, finalize."""
import pytest
import xmlrpc.client


@pytest.fixture
def active_event(odoo, cfg):
    pri = odoo("sentinela.alarm.priority", "search", [[]], {"limit": 1})
    event_id = odoo("sentinela.alarm.event", "create",
                    [{"name": "PYTEST WIZARD", "device_id": cfg["device_id"],
                      "priority_id": pri[0], "status": "active"}])
    yield event_id
    # Cleanup robusto — el evento puede haber pasado a resolved
    try:
        odoo("sentinela.alarm.event", "unlink", [[event_id]])
    except xmlrpc.client.Fault:
        pass


def _open_wizard(odoo, event_id):
    """Crea un wizard tal como lo haría el dashboard JS (con context)."""
    return odoo("sentinela.alarm.handle.wizard", "create",
                [{}], {"context": {"default_alarm_event_id": event_id}})


def test_open_wizard_auto_acknowledges(odoo, active_event):
    """Abrir el wizard debe ejecutar action_acknowledge sobre el evento."""
    _open_wizard(odoo, active_event)
    rec = odoo("sentinela.alarm.event", "read",
               [[active_event], ["status", "current_operator_id", "acknowledged_at"]])[0]
    assert rec["status"] == "acknowledged", \
        f"esperaba status=acknowledged, llegó {rec['status']}"
    assert rec["current_operator_id"], "wizard no hizo auto-claim"
    assert rec["acknowledged_at"], "wizard no seteó acknowledged_at"


def test_wizard_starts_in_verify(odoo, active_event):
    wid = _open_wizard(odoo, active_event)
    rec = odoo("sentinela.alarm.handle.wizard", "read",
               [[wid], ["state"]])[0]
    assert rec["state"] == "verify"


def test_wizard_next_step_advances(odoo, active_event):
    wid = _open_wizard(odoo, active_event)
    odoo("sentinela.alarm.handle.wizard", "action_next_step", [[wid]])
    odoo("sentinela.alarm.handle.wizard", "action_next_step", [[wid]])
    rec = odoo("sentinela.alarm.handle.wizard", "read", [[wid], ["state"]])[0]
    assert rec["state"] == "dispatch"


def test_wizard_prev_step_goes_back(odoo, active_event):
    wid = _open_wizard(odoo, active_event)
    odoo("sentinela.alarm.handle.wizard", "action_next_step", [[wid]])
    odoo("sentinela.alarm.handle.wizard", "action_prev_step", [[wid]])
    rec = odoo("sentinela.alarm.handle.wizard", "read", [[wid], ["state"]])[0]
    assert rec["state"] == "verify"


def test_wizard_shortcut_false_alarm(odoo, active_event):
    wid = _open_wizard(odoo, active_event)
    odoo("sentinela.alarm.handle.wizard", "action_shortcut_false_alarm", [[wid]])
    rec = odoo("sentinela.alarm.handle.wizard", "read",
               [[wid], ["state", "close_reason"]])[0]
    assert rec["state"] == "close"
    assert rec["close_reason"] == "false_alarm"


def test_wizard_shortcut_customer_ok(odoo, active_event):
    wid = _open_wizard(odoo, active_event)
    odoo("sentinela.alarm.handle.wizard", "action_shortcut_customer_ok", [[wid]])
    rec = odoo("sentinela.alarm.handle.wizard", "read",
               [[wid], ["state", "close_reason"]])[0]
    assert rec["state"] == "close"
    assert rec["close_reason"] == "customer_confirmed_ok"


def test_wizard_finalize_without_close_reason_raises(odoo, active_event):
    wid = _open_wizard(odoo, active_event)
    # avanzar al paso close sin setear close_reason
    odoo("sentinela.alarm.handle.wizard", "write", [[wid], {"state": "close"}])
    with pytest.raises(xmlrpc.client.Fault) as excinfo:
        odoo("sentinela.alarm.handle.wizard", "action_finalize", [[wid]])
    assert "motivo" in excinfo.value.faultString.lower()


def test_wizard_finalize_resolves_event(odoo, active_event):
    wid = _open_wizard(odoo, active_event)
    # Avanzar a dispatch, marcar in_progress en el evento para que action_resolve sea válido
    odoo("sentinela.alarm.event", "action_assign_technician", [[active_event]])
    odoo("sentinela.alarm.handle.wizard", "write",
         [[wid], {"state": "close", "close_reason": "verified_real",
                  "final_notes": "evento real verificado por patrulla"}])
    odoo("sentinela.alarm.handle.wizard", "action_finalize", [[wid]])
    rec = odoo("sentinela.alarm.event", "read",
               [[active_event], ["status", "close_reason", "current_operator_id"]])[0]
    assert rec["status"] == "resolved"
    assert rec["close_reason"] == "verified_real"
    assert rec["current_operator_id"] is False, "finalize debe liberar el lock"


def test_wizard_consolidates_bitacora_into_event_notes(odoo, active_event):
    wid = _open_wizard(odoo, active_event)
    odoo("sentinela.alarm.handle.wizard", "write",
         [[wid], {"state": "close", "close_reason": "false_alarm",
                  "notes": "cliente reportó por error",
                  "final_notes": "cerrado tras confirmar con esposa"}])
    odoo("sentinela.alarm.event", "action_assign_technician", [[active_event]])
    odoo("sentinela.alarm.handle.wizard", "action_finalize", [[wid]])
    rec = odoo("sentinela.alarm.event", "read",
               [[active_event], ["resolution_notes"]])[0]
    notes = rec["resolution_notes"] or ""
    assert "cliente reportó por error" in notes
    assert "cerrado tras confirmar con esposa" in notes
