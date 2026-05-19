"""Detección de paneles offline y auto-cierre cuando vuelven a reportar."""


def _trigger_cron(odoo):
    """Dispara el ir.cron 'Detección de Paneles Offline' vía external id."""
    refs = odoo("ir.model.data", "search_read",
                [[("module", "=", "sentinela_monitoring"),
                  ("name", "=", "ir_cron_detect_offline_panels")],
                 ["res_id"]])
    assert refs, "external id sentinela_monitoring.ir_cron_detect_offline_panels no existe"
    cron_id = refs[0]["res_id"]
    odoo("ir.cron", "method_direct_trigger", [[cron_id]])


def _open_offline_events(odoo, device_id):
    return odoo("sentinela.alarm.event", "search",
                [[("device_id", "=", device_id),
                  ("description", "like", "[AUTO_OFFLINE]%"),
                  ("status", "in", ["active", "acknowledged", "in_progress"])]])


def test_cron_creates_trouble_for_overdue_device(odoo, cfg, reset_device):
    """Device con expected_heartbeat_hours bajo y last_comm vieja → trouble [AUTO_OFFLINE]."""
    # Setup: 1 hora de umbral, last_communication 2 horas atrás
    odoo("sentinela.monitoring.device", "write",
         [[cfg["device_id"]],
          {"expected_heartbeat_hours": 1.0, "status": "active"}])
    # Backdate via XML-RPC: setear directamente a un valor fijo viejo
    odoo("sentinela.monitoring.device", "write",
         [[cfg["device_id"]],
          {"last_communication": "2026-01-01 00:00:00"}])

    # Cleanup previo: cerrar cualquier evento [AUTO_OFFLINE] que ya exista
    pre_open = _open_offline_events(odoo, cfg["device_id"])
    if pre_open:
        odoo("sentinela.alarm.event", "write",
             [pre_open, {"status": "closed"}])

    _trigger_cron(odoo)

    opened = _open_offline_events(odoo, cfg["device_id"])
    assert len(opened) == 1, f"esperaba 1 evento [AUTO_OFFLINE], hay {len(opened)}"
    detail = odoo("sentinela.alarm.event", "read",
                  [opened, ["event_type", "status", "description"]])
    assert detail[0]["event_type"] == "trouble"
    assert detail[0]["status"] == "active"
    assert detail[0]["description"].startswith("[AUTO_OFFLINE]")


def test_cron_idempotent(odoo, cfg, reset_device):
    """Correr el cron 2 veces sin cambios en device NO debe duplicar el evento."""
    odoo("sentinela.monitoring.device", "write",
         [[cfg["device_id"]],
          {"expected_heartbeat_hours": 1.0, "status": "active",
           "last_communication": "2026-01-01 00:00:00"}])
    pre_open = _open_offline_events(odoo, cfg["device_id"])
    if pre_open:
        odoo("sentinela.alarm.event", "write", [pre_open, {"status": "closed"}])

    _trigger_cron(odoo)
    first = _open_offline_events(odoo, cfg["device_id"])
    _trigger_cron(odoo)
    second = _open_offline_events(odoo, cfg["device_id"])

    assert len(first) == 1
    assert second == first, "el segundo trigger NO debe crear duplicado"


def test_signal_closes_open_offline_event(odoo, cfg, send_trama, reset_device):
    """Cuando el panel vuelve a reportar, el evento [AUTO_OFFLINE] abierto pasa a resolved."""
    # Forzar la situación: evento offline activo
    odoo("sentinela.monitoring.device", "write",
         [[cfg["device_id"]],
          {"expected_heartbeat_hours": 1.0, "status": "active",
           "last_communication": "2026-01-01 00:00:00"}])
    _trigger_cron(odoo)
    opened = _open_offline_events(odoo, cfg["device_id"])
    assert len(opened) == 1, "setup falló: no se creó el evento offline"
    event_id = opened[0]

    # Panel reporta
    send_trama(cfg["account"], "602", zone="000")

    state = odoo("sentinela.alarm.event", "read",
                 [[event_id], ["status", "resolution_notes"]])
    assert state[0]["status"] == "resolved", \
        f"esperaba status=resolved, llegó {state[0]['status']}"
    assert "Panel reportó" in (state[0]["resolution_notes"] or ""), \
        "resolution_notes debe contener mensaje de recuperación"


def test_cron_skips_devices_without_expected_heartbeat(odoo, cfg, reset_device):
    """Device con expected_heartbeat_hours=0 NO debe disparar evento offline."""
    odoo("sentinela.monitoring.device", "write",
         [[cfg["device_id"]],
          {"expected_heartbeat_hours": 0.0, "status": "active",
           "last_communication": "2026-01-01 00:00:00"}])

    pre_open = _open_offline_events(odoo, cfg["device_id"])
    if pre_open:
        odoo("sentinela.alarm.event", "write", [pre_open, {"status": "closed"}])

    _trigger_cron(odoo)
    after = _open_offline_events(odoo, cfg["device_id"])
    assert after == [], "device con expected_heartbeat_hours=0 NO debe generar trouble"
