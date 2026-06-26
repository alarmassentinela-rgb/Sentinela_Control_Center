# -*- coding: utf-8 -*-
"""W5.2/W5.3 — Validación del flujo OTP + sesiones (mock, sin servicios externos)."""
from app.config import settings
from app.models import AuthAuditEvent
from app.security.tokens import decode_access_token

PHONE = "+528680000001"      # mapeado a partner 25757 (FakeOdooClient)
UNKNOWN = "+520000000000"    # no-cliente


def _req(ctx, phone=PHONE, device="dev1"):
    return ctx.client.post("/v1/auth/otp/request", json={"phone": phone, "device": device})


def _ver(ctx, code, phone=PHONE, device="dev1"):
    return ctx.client.post("/v1/auth/otp/verify", json={"phone": phone, "code": code, "device": device})


def _wrong(code):
    return ("1" + code[1:]) if code[0] != "1" else ("2" + code[1:])


def test_full_flow_login(ctx):
    assert _req(ctx).json()["ok"]
    code = ctx.mock.last_code(PHONE)
    assert code and len(code) == settings.otp_length
    v = _ver(ctx, code)
    assert v.status_code == 200, v.text
    body = v.json()
    assert body["access_token"] and body["refresh_token"]
    claims = decode_access_token(body["access_token"], settings.jwt_secret)
    assert claims["partner_id"] == 25757
    assert claims["typ"] == "access"


def test_otp_only_hashed(ctx):
    from app.models import OtpChallenge
    _req(ctx)
    # El código NO se guarda en claro: solo existe code_hash (distinto del código).
    with ctx.Session() as s:
        row = s.query(OtpChallenge).first()
        assert row is not None
        assert row.code_hash and row.code_hash != ctx.mock.last_code(PHONE)


def test_wrong_code_and_attempt_lock(ctx):
    _req(ctx)
    code = ctx.mock.last_code(PHONE)
    for _ in range(settings.otp_max_attempts):
        assert _ver(ctx, _wrong(code)).status_code == 401
    # tras N intentos el código correcto queda bloqueado
    assert _ver(ctx, code).status_code == 401


def test_expired_code(ctx):
    settings.otp_ttl_sec = 0
    _req(ctx)
    code = ctx.mock.last_code(PHONE)
    r = _ver(ctx, code)
    assert r.status_code == 401 and r.json()["error"] == "invalid"


def test_cooldown(ctx):
    settings.otp_cooldown_sec = 60
    assert _req(ctx).status_code == 200
    r2 = _req(ctx)
    assert r2.status_code == 429 and r2.json()["error"] == "cooldown"


def test_rate_limit_phone(ctx):
    settings.otp_cooldown_sec = 0
    settings.otp_max_per_phone = 2
    assert _req(ctx).status_code == 200
    assert _req(ctx).status_code == 200
    r3 = _req(ctx)
    assert r3.status_code == 429 and r3.json()["error"] == "rate_phone"


def test_refresh_rotation_and_reuse(ctx):
    _req(ctx)
    v = _ver(ctx, ctx.mock.last_code(PHONE)).json()
    rt1 = v["refresh_token"]
    r = ctx.client.post("/v1/auth/refresh", json={"refresh_token": rt1})
    assert r.status_code == 200
    rt2 = r.json()["refresh_token"]
    assert rt2 and rt2 != rt1
    # reuse del refresh viejo -> 401 reuse + revoca familia
    reuse = ctx.client.post("/v1/auth/refresh", json={"refresh_token": rt1})
    assert reuse.status_code == 401 and reuse.json()["error"] == "reuse"
    # el nuevo refresh también queda invalidado (familia revocada)
    assert ctx.client.post("/v1/auth/refresh", json={"refresh_token": rt2}).status_code == 401


def test_logout_revokes(ctx):
    _req(ctx)
    v = _ver(ctx, ctx.mock.last_code(PHONE)).json()
    lo = ctx.client.post("/v1/auth/logout", headers={"Authorization": "Bearer " + v["access_token"]})
    assert lo.status_code == 200
    assert ctx.client.post("/v1/auth/refresh", json={"refresh_token": v["refresh_token"]}).status_code == 401


def test_unknown_phone_is_neutral(ctx):
    assert _req(ctx, phone=UNKNOWN).status_code == 200       # no revela inexistencia
    code = ctx.mock.last_code(UNKNOWN)
    r = _ver(ctx, code, phone=UNKNOWN)
    assert r.status_code == 401 and r.json()["error"] == "invalid"


def test_audit_recorded(ctx):
    _req(ctx)
    _ver(ctx, ctx.mock.last_code(PHONE))
    with ctx.Session() as s:
        types = {e.event_type for e in s.query(AuthAuditEvent).all()}
    assert {"otp_request", "otp_sent", "otp_verify", "login"} <= types
