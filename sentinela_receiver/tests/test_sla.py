"""F2.3 Timer SLA: deadline computed por prioridad, status dinámico."""
import pytest
from datetime import datetime, timedelta, timezone


@pytest.fixture
def sla_priority(odoo):
    """Crea (o reusa) una prioridad con SLA = 10 minutos. Limpia al final."""
    existing = odoo("sentinela.alarm.priority", "search",
                    [[("code", "=", "PYTEST_SLA")]])
    if existing:
        pri_id = existing[0]
        odoo("sentinela.alarm.priority", "write",
             [[pri_id], {"sla_response_minutes": 10}])
    else:
        max_level = odoo("sentinela.alarm.priority", "search_read",
                         [[], ["level"]], {"order": "level desc", "limit": 1})
        new_level = (max_level[0]["level"] + 1) if max_level else 1
        pri_id = odoo("sentinela.alarm.priority", "create",
                      [{"name": "PYTEST SLA", "code": "PYTEST_SLA",
                        "level": new_level, "sla_response_minutes": 10}])
    yield pri_id
    odoo("sentinela.alarm.priority", "unlink", [[pri_id]])


@pytest.fixture
def event_with_sla(odoo, cfg, sla_priority):
    event_id = odoo("sentinela.alarm.event", "create",
                    [{"name": "PYTEST SLA EVENT", "device_id": cfg["device_id"],
                      "priority_id": sla_priority, "status": "active"}])
    yield event_id
    odoo("sentinela.alarm.event", "unlink", [[event_id]])


def test_sla_deadline_computed(odoo, event_with_sla):
    rec = odoo("sentinela.alarm.event", "read",
               [[event_with_sla], ["start_date", "sla_deadline"]])[0]
    start = datetime.strptime(rec["start_date"], "%Y-%m-%d %H:%M:%S")
    deadline = datetime.strptime(rec["sla_deadline"], "%Y-%m-%d %H:%M:%S")
    diff = (deadline - start).total_seconds()
    assert 590 <= diff <= 610, f"deadline-start = {diff}s, esperaba ~600 (10min)"


def test_sla_status_ok_when_fresh(odoo, event_with_sla):
    rec = odoo("sentinela.alarm.event", "read",
               [[event_with_sla], ["sla_status"]])[0]
    assert rec["sla_status"] in ("ok", "warning"), \
        f"esperaba ok/warning recién creado, llegó {rec['sla_status']}"


def test_sla_status_overdue_when_deadline_past(odoo, event_with_sla):
    # Backdate start_date para que el deadline ya pasó
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    odoo("sentinela.alarm.event", "write",
         [[event_with_sla], {"start_date": past}])
    rec = odoo("sentinela.alarm.event", "read",
               [[event_with_sla], ["sla_status"]])[0]
    assert rec["sla_status"] == "overdue", \
        f"esperaba overdue, llegó {rec['sla_status']}"


def test_acknowledge_sets_acknowledged_at(odoo, event_with_sla):
    odoo("sentinela.alarm.event", "action_acknowledge", [[event_with_sla]])
    rec = odoo("sentinela.alarm.event", "read",
               [[event_with_sla], ["acknowledged_at", "sla_status"]])[0]
    assert rec["acknowledged_at"], "acknowledged_at no se seteó"
    assert rec["sla_status"] == "met", \
        f"reconocido a tiempo debe ser 'met', llegó {rec['sla_status']}"


def test_acknowledge_after_deadline_marks_breached(odoo, event_with_sla):
    past = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    odoo("sentinela.alarm.event", "write",
         [[event_with_sla], {"start_date": past}])
    odoo("sentinela.alarm.event", "action_acknowledge", [[event_with_sla]])
    rec = odoo("sentinela.alarm.event", "read",
               [[event_with_sla], ["sla_status"]])[0]
    assert rec["sla_status"] == "breached", \
        f"reconocido tarde debe ser 'breached', llegó {rec['sla_status']}"


def test_no_sla_when_priority_has_zero(odoo, cfg):
    """Prioridad sin SLA → sla_status='no_sla', sla_deadline=False."""
    base = odoo("sentinela.alarm.priority", "search_read",
                [[("sla_response_minutes", "=", 0)], ["id"]], {"limit": 1})
    if not base:
        pytest.skip("no hay prioridad con sla_response_minutes=0")
    event_id = odoo("sentinela.alarm.event", "create",
                    [{"name": "PYTEST NO SLA", "device_id": cfg["device_id"],
                      "priority_id": base[0]["id"], "status": "active"}])
    try:
        rec = odoo("sentinela.alarm.event", "read",
                   [[event_id], ["sla_deadline", "sla_status"]])[0]
        assert rec["sla_deadline"] is False
        assert rec["sla_status"] == "no_sla"
    finally:
        odoo("sentinela.alarm.event", "unlink", [[event_id]])


def test_re_acknowledge_does_not_reset_timer(odoo, event_with_sla):
    """Re-acknowledge no debe resetear acknowledged_at."""
    odoo("sentinela.alarm.event", "action_acknowledge", [[event_with_sla]])
    first = odoo("sentinela.alarm.event", "read",
                 [[event_with_sla], ["acknowledged_at"]])[0]["acknowledged_at"]
    # forzar otro acknowledge (status revertido)
    odoo("sentinela.alarm.event", "write",
         [[event_with_sla], {"status": "active"}])
    odoo("sentinela.alarm.event", "action_acknowledge", [[event_with_sla]])
    second = odoo("sentinela.alarm.event", "read",
                  [[event_with_sla], ["acknowledged_at"]])[0]["acknowledged_at"]
    assert first == second, "acknowledged_at debe preservarse en re-ack"
