"""F2.5 Audio por prioridad — backend method get_audio_state."""
import pytest


@pytest.fixture
def event_with_priority(odoo, cfg):
    pri = odoo("sentinela.alarm.priority", "search", [[]], {"limit": 1})
    event_id = odoo("sentinela.alarm.event", "create",
                    [{"name": "PYTEST AUDIO", "device_id": cfg["device_id"],
                      "priority_id": pri[0], "status": "active"}])
    yield event_id, pri[0]
    odoo("sentinela.alarm.event", "unlink", [[event_id]])


def test_get_audio_state_returns_active_alarms(odoo, event_with_priority):
    event_id, _pri_id = event_with_priority
    res = odoo("sentinela.alarm.event", "get_audio_state", [])
    assert "active_alarms" in res
    ids = [a["event_id"] for a in res["active_alarms"]]
    assert event_id in ids, f"esperaba event_id {event_id} en active_alarms, llegó {ids}"


def test_get_audio_state_structure(odoo, event_with_priority):
    event_id, _ = event_with_priority
    res = odoo("sentinela.alarm.event", "get_audio_state", [])
    entry = next(a for a in res["active_alarms"] if a["event_id"] == event_id)
    expected_keys = {"event_id", "priority_id", "priority_level", "priority_name",
                     "has_sound", "sound_url", "is_reminder", "is_claimed_by_me"}
    assert expected_keys.issubset(entry.keys()), \
        f"faltan keys: {expected_keys - entry.keys()}"


def test_get_audio_state_marks_claimed_by_me(odoo, event_with_priority):
    """Si quien llama tiene el lock, is_claimed_by_me=True para ese evento."""
    event_id, _ = event_with_priority
    odoo("sentinela.alarm.event", "action_claim_event", [[event_id]])
    res = odoo("sentinela.alarm.event", "get_audio_state", [])
    entry = next(a for a in res["active_alarms"] if a["event_id"] == event_id)
    assert entry["is_claimed_by_me"] is True, \
        "el evento claimed por el caller debe marcarse is_claimed_by_me"


def test_get_audio_state_excludes_resolved(odoo, cfg):
    """Eventos resolved no deben aparecer en active_alarms."""
    pri = odoo("sentinela.alarm.priority", "search", [[]], {"limit": 1})
    event_id = odoo("sentinela.alarm.event", "create",
                    [{"name": "PYTEST AUDIO RESOLVED",
                      "device_id": cfg["device_id"],
                      "priority_id": pri[0], "status": "active"}])
    try:
        odoo("sentinela.alarm.event", "action_acknowledge", [[event_id]])
        odoo("sentinela.alarm.event", "action_assign_technician", [[event_id]])
        odoo("sentinela.alarm.event", "write",
             [[event_id], {"close_reason": "false_alarm"}])
        odoo("sentinela.alarm.event", "action_resolve", [[event_id]])
        res = odoo("sentinela.alarm.event", "get_audio_state", [])
        ids = [a["event_id"] for a in res["active_alarms"]]
        assert event_id not in ids, \
            "evento resolved NO debe estar en active_alarms"
    finally:
        odoo("sentinela.alarm.event", "unlink", [[event_id]])


def test_sound_url_format_when_has_sound(odoo, cfg):
    """sound_url debe apuntar al /web/content/ de la prioridad cuando hay binary."""
    # Crear una prioridad con priority_sound (1 byte dummy en base64)
    max_level = odoo("sentinela.alarm.priority", "search_read",
                     [[], ["level"]], {"order": "level desc", "limit": 1})
    new_level = (max_level[0]["level"] + 1) if max_level else 1
    pri_id = odoo("sentinela.alarm.priority", "create",
                  [{"name": "PYTEST_AUDIO_PRI", "code": "PYTEST_AUDIO",
                    "level": new_level,
                    "priority_sound": "AAA=",  # dummy base64
                    "priority_sound_filename": "test.mp3"}])
    event_id = odoo("sentinela.alarm.event", "create",
                    [{"name": "PYTEST AUDIO PRI", "device_id": cfg["device_id"],
                      "priority_id": pri_id, "status": "active"}])
    try:
        res = odoo("sentinela.alarm.event", "get_audio_state", [])
        entry = next(a for a in res["active_alarms"] if a["event_id"] == event_id)
        assert entry["has_sound"] is True
        assert entry["sound_url"] and "/web/content/sentinela.alarm.priority/" in entry["sound_url"]
        assert "test.mp3" in entry["sound_url"]
    finally:
        odoo("sentinela.alarm.event", "unlink", [[event_id]])
        odoo("sentinela.alarm.priority", "unlink", [[pri_id]])
