"""F2.2 Motivos de cierre estructurados: close_reason obligatorio al resolver/cerrar."""
import pytest
import xmlrpc.client


@pytest.fixture
def claimed_event(odoo, cfg):
    """Evento creado, claim tomado y status=in_progress (listo para resolver)."""
    pri = odoo("sentinela.alarm.priority", "search", [[]], {"limit": 1})
    if not pri:
        pytest.skip("no hay sentinela.alarm.priority en la DB")
    event_id = odoo("sentinela.alarm.event", "create",
                    [{"name": "PYTEST CLOSE", "device_id": cfg["device_id"],
                      "priority_id": pri[0], "status": "active"}])
    odoo("sentinela.alarm.event", "action_acknowledge", [[event_id]])
    odoo("sentinela.alarm.event", "action_assign_technician", [[event_id]])
    yield event_id
    odoo("sentinela.alarm.event", "unlink", [[event_id]])


def test_resolve_without_close_reason_raises(odoo, claimed_event):
    with pytest.raises(xmlrpc.client.Fault) as excinfo:
        odoo("sentinela.alarm.event", "action_resolve", [[claimed_event]])
    assert "motivo de cierre" in excinfo.value.faultString.lower()


def test_resolve_with_close_reason_succeeds(odoo, claimed_event):
    odoo("sentinela.alarm.event", "write",
         [[claimed_event], {"close_reason": "false_alarm"}])
    odoo("sentinela.alarm.event", "action_resolve", [[claimed_event]])
    rec = odoo("sentinela.alarm.event", "read",
               [[claimed_event], ["status", "close_reason"]])[0]
    assert rec["status"] == "resolved"
    assert rec["close_reason"] == "false_alarm"


def test_resolve_with_other_requires_notes(odoo, claimed_event):
    odoo("sentinela.alarm.event", "write",
         [[claimed_event], {"close_reason": "other"}])
    with pytest.raises(xmlrpc.client.Fault) as excinfo:
        odoo("sentinela.alarm.event", "action_resolve", [[claimed_event]])
    assert "notas" in excinfo.value.faultString.lower()


def test_resolve_with_other_and_notes_succeeds(odoo, claimed_event):
    odoo("sentinela.alarm.event", "write",
         [[claimed_event], {"close_reason": "other",
                            "resolution_notes": "cliente pidió cancelar"}])
    odoo("sentinela.alarm.event", "action_resolve", [[claimed_event]])
    rec = odoo("sentinela.alarm.event", "read",
               [[claimed_event], ["status"]])[0]
    assert rec["status"] == "resolved"


def test_auto_offline_recovery_sets_close_reason(odoo, cfg, send_trama, reset_device):
    """Cuando el panel reporta tras un evento [AUTO_OFFLINE], se debe auto-setear
    close_reason='auto_offline_recovered'."""
    # Forzar evento offline
    odoo("sentinela.monitoring.device", "write",
         [[cfg["device_id"]],
          {"expected_heartbeat_hours": 1.0, "status": "active",
           "last_communication": "2026-01-01 00:00:00"}])
    cron_ref = odoo("ir.model.data", "search_read",
                    [[("module", "=", "sentinela_monitoring"),
                      ("name", "=", "ir_cron_detect_offline_panels")], ["res_id"]])
    odoo("ir.cron", "method_direct_trigger", [[cron_ref[0]["res_id"]]])
    opened = odoo("sentinela.alarm.event", "search",
                  [[("device_id", "=", cfg["device_id"]),
                    ("description", "like", "[AUTO_OFFLINE]%"),
                    ("status", "=", "active")]])
    assert opened, "setup falló — no se creó evento [AUTO_OFFLINE]"
    event_id = opened[0]

    # Panel reporta
    send_trama(cfg["account"], "602", zone="000")

    rec = odoo("sentinela.alarm.event", "read",
               [[event_id], ["status", "close_reason"]])[0]
    assert rec["status"] == "resolved"
    assert rec["close_reason"] == "auto_offline_recovered", \
        f"esperaba auto_offline_recovered, llegó {rec['close_reason']}"
