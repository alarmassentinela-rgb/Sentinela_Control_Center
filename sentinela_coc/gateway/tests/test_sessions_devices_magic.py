# -*- coding: utf-8 -*-
"""W5.5/W5.9/W5.10 — sesiones, dispositivos, magic links, historial, notificaciones."""
from app.models import PortalSession
from app.services import session_service

P1 = "+528680000001"   # -> 25757
P2 = "+528680000002"   # -> 25758


def _login(ctx, phone=P1, device="devA"):
    ctx.client.post("/v1/auth/otp/request", json={"phone": phone, "device": device})
    code = ctx.mock.last_code(phone)
    return ctx.client.post("/v1/auth/otp/verify", json={"phone": phone, "code": code, "device": device}).json()


def _auth(tok):
    return {"Authorization": "Bearer " + tok}


# ---- Centro de sesiones ----
def test_sessions_list_and_close(ctx):
    a = _login(ctx, device="devA")
    b = _login(ctx, device="devB")
    r = ctx.client.get("/v1/sessions", headers=_auth(b["access_token"]))
    sess = r.json()["sessions"]
    assert len(sess) == 2
    assert sum(1 for s in sess if s["current"]) == 1
    assert ctx.client.delete(f"/v1/sessions/{a['session_id']}", headers=_auth(b["access_token"])).status_code == 200
    assert len(ctx.client.get("/v1/sessions", headers=_auth(b["access_token"])).json()["sessions"]) == 1


def test_close_all_keeps_current(ctx):
    _login(ctx); _login(ctx)
    c = _login(ctx)
    r = ctx.client.post("/v1/sessions/close-all", headers=_auth(c["access_token"]))
    assert r.json()["closed"] == 2
    assert len(ctx.client.get("/v1/sessions", headers=_auth(c["access_token"])).json()["sessions"]) == 1


def test_cannot_close_other_partner_session(ctx):
    p1 = _login(ctx, phone=P1)
    p2 = _login(ctx, phone=P2)
    assert ctx.client.delete(f"/v1/sessions/{p2['session_id']}", headers=_auth(p1["access_token"])).status_code == 404
    assert ctx.client.get("/v1/sessions", headers=_auth(p2["access_token"])).status_code == 200


def test_access_token_revoked_after_close(ctx):
    a = _login(ctx)
    ctx.client.delete(f"/v1/sessions/{a['session_id']}", headers=_auth(a["access_token"]))
    assert ctx.client.get("/v1/sessions", headers=_auth(a["access_token"])).status_code == 401


# ---- Dispositivos confiables ----
def test_devices_trust_and_remove(ctx):
    a = _login(ctx, device="mi-celular")
    devs = ctx.client.get("/v1/devices", headers=_auth(a["access_token"])).json()["devices"]
    assert len(devs) == 1 and devs[0]["trusted"] is False
    pk = devs[0]["id"]
    assert ctx.client.post(f"/v1/devices/{pk}/trust", headers=_auth(a["access_token"])).json()["trusted"] is True
    assert ctx.client.delete(f"/v1/devices/{pk}/trust", headers=_auth(a["access_token"])).json()["trusted"] is False
    assert ctx.client.delete(f"/v1/devices/{pk}", headers=_auth(a["access_token"])).status_code == 200
    # al eliminar el dispositivo se revoca su sesión
    assert ctx.client.get("/v1/devices", headers=_auth(a["access_token"])).status_code == 401


# ---- Notificación de nuevo inicio de sesión ----
def test_new_login_notification(ctx):
    _login(ctx, device="dev-nuevo")
    assert len(ctx.notifier.events) == 1
    _login(ctx, device="dev-nuevo")        # mismo device -> sin nueva notif
    assert len(ctx.notifier.events) == 1
    _login(ctx, device="otro-dev")         # device nuevo -> notif
    assert len(ctx.notifier.events) == 2


# ---- Historial de accesos ----
def test_access_history(ctx):
    a = _login(ctx)
    r = ctx.client.get("/v1/access-history", headers=_auth(a["access_token"]))
    assert "login" in {e["event_type"] for e in r.json()["events"]}


# ---- Revocación al cambiar credenciales críticas ----
def test_credential_change_revokes_others(ctx):
    a = _login(ctx)
    _login(ctx)
    with ctx.Session() as s:
        identity_id = s.query(PortalSession).first().identity_id
        n = session_service.revoke_all_on_credential_change(s, ctx.fake, identity_id, keep_session_id=a["session_id"])
        s.commit()
    assert n == 1
    assert ctx.client.get("/v1/sessions", headers=_auth(a["access_token"])).status_code == 200


# ---- Magic links de un solo uso ----
def test_magic_issue_consume_single_use(ctx):
    h = {"X-COC-Secret": "test-secret"}
    tok = ctx.client.post("/coc/internal/magic/issue", json={
        "purpose": "sign_document", "partner_id": 25757,
        "res_model": "sentinela.sign.document", "res_id": 5, "ttl_sec": 600}, headers=h).json()["token"]
    c = ctx.client.post("/v1/magic/consume", json={"token": tok})
    assert c.status_code == 200 and c.json()["purpose"] == "sign_document" and c.json()["partner_id"] == 25757
    c2 = ctx.client.post("/v1/magic/consume", json={"token": tok})   # segundo uso
    assert c2.status_code == 400 and c2.json()["error"] == "used"


def test_magic_requires_secret(ctx):
    r = ctx.client.post("/coc/internal/magic/issue", json={"purpose": "x", "partner_id": 1},
                        headers={"X-COC-Secret": "wrong"})
    assert r.status_code == 403


def test_magic_expired(ctx):
    h = {"X-COC-Secret": "test-secret"}
    tok = ctx.client.post("/coc/internal/magic/issue",
                          json={"purpose": "x", "partner_id": 1, "ttl_sec": 0}, headers=h).json()["token"]
    r = ctx.client.post("/v1/magic/consume", json={"token": tok})
    assert r.status_code == 400 and r.json()["error"] == "expired"
