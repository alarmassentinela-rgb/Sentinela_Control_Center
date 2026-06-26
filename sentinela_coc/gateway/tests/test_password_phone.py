# -*- coding: utf-8 -*-
"""W5.8 — contraseñas Argon2, cambio, recuperación por OTP, cambio de teléfono."""
PHONE = "+528680000001"   # -> 25757
GOOD = "abc12345"
GOOD2 = "xyz98765"


def _otp_login(ctx, phone=PHONE, device="devA"):
    ctx.client.post("/v1/auth/otp/request", json={"phone": phone, "device": device})
    code = ctx.mock.last_code(phone)
    return ctx.client.post("/v1/auth/otp/verify", json={"phone": phone, "code": code, "device": device}).json()


def _auth(tok):
    return {"Authorization": "Bearer " + tok}


def test_password_policy_rejected(ctx):
    a = _otp_login(ctx)
    r = ctx.client.post("/v1/auth/password", json={"new_password": "1234567"}, headers=_auth(a["access_token"]))
    assert r.status_code == 400 and r.json()["error"] == "policy"


def test_set_password_revokes_other_sessions(ctx):
    a = _otp_login(ctx, device="A")
    b = _otp_login(ctx, device="B")
    r = ctx.client.post("/v1/auth/password", json={"new_password": GOOD}, headers=_auth(b["access_token"]))
    assert r.status_code == 200 and r.json()["ok"]
    # la sesión actual (B) sigue; la otra (A) queda revocada
    assert ctx.client.get("/v1/sessions", headers=_auth(b["access_token"])).status_code == 200
    assert ctx.client.get("/v1/sessions", headers=_auth(a["access_token"])).status_code == 401


def test_password_login(ctx):
    a = _otp_login(ctx)
    ctx.client.post("/v1/auth/password", json={"new_password": GOOD}, headers=_auth(a["access_token"]))
    # login con contraseña
    ok = ctx.client.post("/v1/auth/password/login", json={"phone": PHONE, "password": GOOD, "device": "pw"})
    assert ok.status_code == 200 and ok.json()["access_token"]
    bad = ctx.client.post("/v1/auth/password/login", json={"phone": PHONE, "password": "wrongwrong", "device": "pw"})
    assert bad.status_code == 401


def test_change_password_requires_current(ctx):
    a = _otp_login(ctx)
    ctx.client.post("/v1/auth/password", json={"new_password": GOOD}, headers=_auth(a["access_token"]))
    # sin current -> error
    r = ctx.client.post("/v1/auth/password", json={"new_password": GOOD2}, headers=_auth(a["access_token"]))
    assert r.status_code == 400 and r.json()["error"] == "current_required"
    # current incorrecto
    r2 = ctx.client.post("/v1/auth/password",
                         json={"new_password": GOOD2, "current_password": "nope12345"}, headers=_auth(a["access_token"]))
    assert r2.status_code == 400 and r2.json()["error"] == "bad_current"
    # current correcto -> cambia
    r3 = ctx.client.post("/v1/auth/password",
                         json={"new_password": GOOD2, "current_password": GOOD}, headers=_auth(a["access_token"]))
    assert r3.status_code == 200
    # la vieja ya no sirve, la nueva sí
    assert ctx.client.post("/v1/auth/password/login", json={"phone": PHONE, "password": GOOD}).status_code == 401
    assert ctx.client.post("/v1/auth/password/login", json={"phone": PHONE, "password": GOOD2}).status_code == 200


def test_recover_via_otp(ctx):
    a = _otp_login(ctx)
    ctx.client.post("/v1/auth/password", json={"new_password": GOOD}, headers=_auth(a["access_token"]))
    # recuperación: request (neutral) + confirm con OTP
    assert ctx.client.post("/v1/auth/recover/request", json={"phone": PHONE}).status_code == 200
    code = ctx.mock.last_code(PHONE)
    r = ctx.client.post("/v1/auth/recover/confirm", json={"phone": PHONE, "code": code, "new_password": GOOD2})
    assert r.status_code == 200 and r.json()["ok"]
    # login con la nueva contraseña
    assert ctx.client.post("/v1/auth/password/login", json={"phone": PHONE, "password": GOOD2}).status_code == 200


def test_phone_change_double_verification(ctx):
    new_phone = "+528680000099"
    a = _otp_login(ctx)
    req = ctx.client.post("/v1/auth/phone/change/request", json={"new_phone": new_phone}, headers=_auth(a["access_token"]))
    assert req.status_code == 200 and req.json()["double_verification"] is True
    code_new = ctx.mock.last_code(new_phone)
    code_cur = ctx.mock.last_code(PHONE)
    # falta el código del teléfono actual -> error (NO consume el código nuevo)
    miss = ctx.client.post("/v1/auth/phone/change/confirm",
                           json={"new_phone": new_phone, "code_new": code_new}, headers=_auth(a["access_token"]))
    assert miss.status_code == 400 and miss.json()["error"] == "current_code_required"
    # con ambos códigos -> cambia y revoca todas las sesiones (incluida la actual)
    ok = ctx.client.post("/v1/auth/phone/change/confirm",
                         json={"new_phone": new_phone, "code_new": code_new, "code_current": code_cur},
                         headers=_auth(a["access_token"]))
    assert ok.status_code == 200 and ok.json()["ok"]
    # tras cambiar credenciales, la sesión actual queda revocada
    assert ctx.client.get("/v1/sessions", headers=_auth(a["access_token"])).status_code == 401
    # y el login OTP ahora resuelve el teléfono NUEVO al partner
    new_login = _otp_login(ctx, phone=new_phone, device="dn")
    assert new_login.get("access_token")
