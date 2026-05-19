"""F2.7.1 — Token de autorización web: creación, authorize, reject."""
import pytest
import urllib.request
import urllib.parse
import xmlrpc.client


@pytest.fixture
def event_token(odoo, cfg):
    """Crea evento + token de autorización para patrullaje $350."""
    pri = odoo("sentinela.alarm.priority", "search", [[]], {"limit": 1})
    event_id = odoo("sentinela.alarm.event", "create",
                    [{"name": "PYTEST AUTH", "device_id": cfg["device_id"],
                      "priority_id": pri[0], "status": "active"}])
    token_id = odoo("sentinela.service.authorization.token", "create",
                    [{"alarm_event_id": event_id, "service_type": "patrol",
                      "amount": 350.0}])
    yield event_id, token_id
    # Cleanup
    try:
        odoo("sentinela.service.authorization.token", "unlink", [[token_id]])
    except xmlrpc.client.Fault:
        pass
    try:
        odoo("sentinela.alarm.event", "unlink", [[event_id]])
    except xmlrpc.client.Fault:
        pass


def test_token_auto_generated_on_create(odoo, event_token):
    event_id, token_id = event_token
    rec = odoo("sentinela.service.authorization.token", "read",
               [[token_id], ["token", "state", "amount"]])[0]
    assert rec["token"], "token debe auto-generarse"
    assert len(rec["token"]) >= 20, "token debe ser secret-grade"
    assert rec["state"] == "pending"
    assert rec["amount"] == 350.0


def test_authorize_marks_event_authorized(odoo, event_token, cfg):
    event_id, token_id = event_token
    odoo("sentinela.service.authorization.token", "authorize",
         [[token_id], "192.168.1.100", "pytest"])
    # Token quedó authorized
    rec = odoo("sentinela.service.authorization.token", "read",
               [[token_id], ["state", "response_ip", "responded_at"]])[0]
    assert rec["state"] == "authorized"
    assert rec["response_ip"] == "192.168.1.100"
    assert rec["responded_at"], "responded_at debe registrarse"
    # Evento quedó extra_service_authorized=True
    ev = odoo("sentinela.alarm.event", "read",
              [[event_id], ["extra_service_authorized"]])[0]
    assert ev["extra_service_authorized"] is True


def test_reject_does_not_authorize_event(odoo, event_token):
    event_id, token_id = event_token
    odoo("sentinela.service.authorization.token", "reject",
         [[token_id], "10.0.0.5", "pytest-reject"])
    rec = odoo("sentinela.service.authorization.token", "read",
               [[token_id], ["state", "response_ip"]])[0]
    assert rec["state"] == "rejected"
    assert rec["response_ip"] == "10.0.0.5"
    ev = odoo("sentinela.alarm.event", "read",
              [[event_id], ["extra_service_authorized"]])[0]
    assert ev["extra_service_authorized"] is False, \
        "rechazar NO debe autorizar el evento"


def test_authorize_twice_raises(odoo, event_token):
    """Re-llamar authorize en un token ya usado debe levantar UserError."""
    event_id, token_id = event_token
    odoo("sentinela.service.authorization.token", "authorize", [[token_id]])
    with pytest.raises(xmlrpc.client.Fault) as excinfo:
        odoo("sentinela.service.authorization.token", "authorize", [[token_id]])
    assert "no se puede autorizar de nuevo" in excinfo.value.faultString.lower()


@pytest.mark.skipif(
    True,
    reason="HTTP routing OK (bug resuelto con dbfilter=^Sentinela_V18$), pero tests "
    "crean tokens en SENTINELA_TEST_DB (default STAGING) y el request HTTP sin sesión "
    "va a V18 por el dbfilter. Para correr: setear SENTINELA_TEST_DB=Sentinela_V18 "
    "o quitar dbfilter temporalmente. Validación manual con curl ya hecha 19-may.")
def test_public_url_works(odoo, event_token, cfg):
    """GET /sentinela/autorizar/<token> devuelve 200 y muestra el formulario."""
    event_id, token_id = event_token
    rec = odoo("sentinela.service.authorization.token", "read",
               [[token_id], ["token"]])[0]
    token = rec["token"]
    # GET
    url = f"http://192.168.3.2:8070/sentinela/autorizar/{token}"
    resp = urllib.request.urlopen(url, timeout=10)
    assert resp.status == 200
    body = resp.read().decode("utf-8")
    assert "AUTORIZO" in body
    assert "RECHAZO" in body
    assert "PYTEST AUTH" in body or "350" in body


@pytest.mark.skipif(
    True,
    reason="HTTP routing OK pero ver test_public_url_works — dbfilter desalinea "
    "test_db (STAGING) con la DB que sirve HTTP (V18). Validación manual hecha.")
def test_public_post_authorize_via_web(odoo, event_token):
    """POST con decision=authorize procesa via controller y actualiza evento."""
    event_id, token_id = event_token
    rec = odoo("sentinela.service.authorization.token", "read",
               [[token_id], ["token"]])[0]
    token = rec["token"]
    url = f"http://192.168.3.2:8070/sentinela/autorizar/{token}"
    data = urllib.parse.urlencode({"decision": "authorize"}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST",
                                  headers={"User-Agent": "pytest-web-flow/1.0"})
    resp = urllib.request.urlopen(req, timeout=10)
    assert resp.status == 200
    body = resp.read().decode("utf-8")
    assert "registrada" in body.lower() or "autorización" in body.lower()
    # Verificar que el evento quedó autorizado
    ev = odoo("sentinela.alarm.event", "read",
              [[event_id], ["extra_service_authorized"]])[0]
    assert ev["extra_service_authorized"] is True
    # Verificar IP/UA registrado
    tk_rec = odoo("sentinela.service.authorization.token", "read",
                  [[token_id], ["state", "response_user_agent"]])[0]
    assert tk_rec["state"] == "authorized"
    assert "pytest-web-flow" in (tk_rec["response_user_agent"] or "")
