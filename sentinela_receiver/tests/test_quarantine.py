"""Cuarentena: cuenta desconocida → signal con is_quarantine=True, sin device ni event."""
import pytest


def _pick_unused_account(odoo):
    """Encuentra una cuenta numérica de 4 dígitos libre. El parser Contact ID
    acepta \\w{1,4} → máx 4 chars."""
    for n in range(9100, 10000):
        candidate = str(n)
        exists = odoo("sentinela.monitoring.device", "search_count",
                      [[("account_number", "=", candidate)]])
        if not exists:
            return candidate
    pytest.skip("no se encontró una cuenta libre 9100-9999")


@pytest.fixture
def unknown_account(odoo, cleanup_quarantine):
    acc = _pick_unused_account(odoo)
    cleanup_quarantine(acc)
    return acc


def test_unknown_account_creates_quarantine_signal(odoo, send_trama, unknown_account):
    send_trama(unknown_account, "130", zone="003")

    signals = odoo("sentinela.alarm.signal", "search_read",
                   [[("quarantine_account", "=", unknown_account)],
                    ["is_quarantine", "alarm_code", "zone", "device_id"]],
                   {"order": "id desc", "limit": 1})
    assert len(signals) == 1, "esperaba 1 signal en cuarentena"
    s = signals[0]
    assert s["is_quarantine"] is True
    assert s["alarm_code"] == "E130"
    assert s["zone"] == "003"
    assert s["device_id"] is False, "signal en cuarentena NO debe tener device"


def test_unknown_account_does_not_create_device(odoo, send_trama, unknown_account):
    send_trama(unknown_account, "130", zone="004")
    devs = odoo("sentinela.monitoring.device", "search_count",
                [[("account_number", "=", unknown_account)]])
    assert devs == 0, "cuarentena NO debe crear monitoring.device"


def test_unknown_account_does_not_create_event(odoo, send_trama, unknown_account):
    send_trama(unknown_account, "130", zone="005")
    events = odoo("sentinela.alarm.event", "search_count",
                  [[("account_number", "=", unknown_account)]])
    assert events == 0, "cuarentena NO debe crear alarm.event"
