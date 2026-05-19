"""Flujo normal: señal de cuenta conocida → signal + event + last_communication."""
from datetime import datetime, timedelta, timezone


def test_known_account_creates_signal(odoo, cfg, send_trama):
    """Trama de cuenta conocida crea una sentinela.alarm.signal con device."""
    before = odoo("sentinela.alarm.signal", "search_count",
                  [[("device_id", "=", cfg["device_id"])]])
    send_trama(cfg["account"], "130", zone="099")
    after = odoo("sentinela.alarm.signal", "search_count",
                 [[("device_id", "=", cfg["device_id"])]])
    assert after == before + 1, f"esperaba +1 signal, se creó {after - before}"

    latest = odoo("sentinela.alarm.signal", "search_read",
                  [[("device_id", "=", cfg["device_id"])],
                   ["alarm_code", "zone", "is_quarantine"]],
                  {"order": "id desc", "limit": 1})
    assert latest[0]["alarm_code"] == "E130"
    assert latest[0]["zone"] == "099"
    assert latest[0]["is_quarantine"] is False


def test_known_account_creates_event(odoo, cfg, send_trama):
    """Código que requiere atención crea un sentinela.alarm.event activo."""
    before = odoo("sentinela.alarm.event", "search_count",
                  [[("device_id", "=", cfg["device_id"]), ("alarm_code_id.code", "=", "130")]])
    send_trama(cfg["account"], "130", zone="098")
    after = odoo("sentinela.alarm.event", "search_count",
                 [[("device_id", "=", cfg["device_id"]), ("alarm_code_id.code", "=", "130")]])
    assert after == before + 1

    latest = odoo("sentinela.alarm.event", "search_read",
                  [[("device_id", "=", cfg["device_id"]), ("alarm_code_id.code", "=", "130")],
                   ["status", "zone"]],
                  {"order": "id desc", "limit": 1})
    assert latest[0]["status"] == "active"
    assert latest[0]["zone"] == "098"


def test_known_account_updates_last_communication(odoo, cfg, send_trama):
    """Tras la señal, device.last_communication debe ser reciente (< 30s)."""
    send_trama(cfg["account"], "602", zone="000")
    dev = odoo("sentinela.monitoring.device", "read",
               [[cfg["device_id"]], ["last_communication"]])
    last = datetime.strptime(dev[0]["last_communication"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    age = datetime.now(timezone.utc) - last
    assert age < timedelta(seconds=30), f"last_communication tiene {age} de antigüedad"
