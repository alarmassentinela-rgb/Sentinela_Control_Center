"""F2.1 Claim/Mutex operador: lock por evento, auto-claim, cron de timeout."""
import pytest
import xmlrpc.client


@pytest.fixture
def fresh_event(odoo, cfg):
    """Crea un evento active con device de prueba, limpia al final."""
    pri = odoo("sentinela.alarm.priority", "search", [[]], {"limit": 1})
    if not pri:
        pytest.skip("no hay sentinela.alarm.priority en la DB")
    event_id = odoo("sentinela.alarm.event", "create",
                    [{"name": "PYTEST CLAIM", "device_id": cfg["device_id"],
                      "priority_id": pri[0], "status": "active"}])
    yield event_id
    odoo("sentinela.alarm.event", "unlink", [[event_id]])


def test_claim_sets_holder(odoo, fresh_event):
    odoo("sentinela.alarm.event", "action_claim_event", [[fresh_event]])
    rec = odoo("sentinela.alarm.event", "read",
               [[fresh_event], ["current_operator_id", "claimed_at"]])[0]
    assert rec["current_operator_id"], "current_operator_id no se seteó"
    assert rec["claimed_at"], "claimed_at no se seteó"


def test_release_clears_holder(odoo, fresh_event):
    odoo("sentinela.alarm.event", "action_claim_event", [[fresh_event]])
    odoo("sentinela.alarm.event", "action_release_event", [[fresh_event]])
    rec = odoo("sentinela.alarm.event", "read",
               [[fresh_event], ["current_operator_id"]])[0]
    assert rec["current_operator_id"] is False


def test_acknowledge_auto_claims(odoo, fresh_event):
    odoo("sentinela.alarm.event", "action_acknowledge", [[fresh_event]])
    rec = odoo("sentinela.alarm.event", "read",
               [[fresh_event], ["current_operator_id", "status"]])[0]
    assert rec["current_operator_id"], "acknowledge no hizo auto-claim"
    assert rec["status"] == "acknowledged"


def test_action_without_claim_raises(odoo, fresh_event):
    with pytest.raises(xmlrpc.client.Fault) as excinfo:
        odoo("sentinela.alarm.event", "action_resolve", [[fresh_event]])
    assert "Toma el evento" in excinfo.value.faultString


def test_cron_releases_stale_lock(odoo, fresh_event):
    odoo("sentinela.alarm.event", "action_claim_event", [[fresh_event]])
    odoo("sentinela.alarm.event", "write",
         [[fresh_event], {"claimed_at": "2026-01-01 00:00:00"}])
    cron_ref = odoo("ir.model.data", "search_read",
                    [[("module", "=", "sentinela_monitoring"),
                      ("name", "=", "ir_cron_release_stale_locks")], ["res_id"]])
    assert cron_ref, "external id ir_cron_release_stale_locks no existe"
    odoo("ir.cron", "method_direct_trigger", [[cron_ref[0]["res_id"]]])
    rec = odoo("sentinela.alarm.event", "read",
               [[fresh_event], ["current_operator_id"]])[0]
    assert rec["current_operator_id"] is False, "cron NO liberó el lock viejo"


def test_cron_skips_fresh_lock(odoo, fresh_event):
    odoo("sentinela.alarm.event", "action_claim_event", [[fresh_event]])
    cron_ref = odoo("ir.model.data", "search_read",
                    [[("module", "=", "sentinela_monitoring"),
                      ("name", "=", "ir_cron_release_stale_locks")], ["res_id"]])
    odoo("ir.cron", "method_direct_trigger", [[cron_ref[0]["res_id"]]])
    rec = odoo("sentinela.alarm.event", "read",
               [[fresh_event], ["current_operator_id"]])[0]
    assert rec["current_operator_id"], "cron robó un lock fresco"
