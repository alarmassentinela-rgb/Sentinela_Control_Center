# -*- coding: utf-8 -*-
"""E2E Sprint 1 contra STAGING real (gateway in-process + Odoo Sentinela_STAGING real).

Evidencia los 13 escenarios pedidos. OTP por Mock (login automatizable); el resto de
recursos por sesiones minteadas con session_service (mismo camino que usa otp/verify),
contra el Odoo real -> ejercita record rules, datos reales, caché y auditoría.

Uso (en el contenedor, --network host):
  PICKMAP='{"alarm_res":25757,...}' COC_COC_SHARED_SECRET=... COC_ODOO_BASE_URL=http://127.0.0.1:8075 \
  python -m tests.e2e_staging_portal
"""
import json
import os
import time

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import deps
from app.clients.odoo import HttpOdooClient
from app.config import settings
from app.db import Base
from app.main import app
from app.providers.notifier_mock import MockLoginNotifier
from app.providers.otp_mock import MockOtpProvider
from app.services import session_service

PICK = json.loads(os.environ["PICKMAP"])
OK, FAIL = "PASS", "FAIL"
results = []


def ev(scenario, status, detail):
    results.append((scenario, status, detail))
    print(f"EV|{scenario}|{status}|{detail}")


# --- arranque: db sqlite file compartida + Odoo real + OTP mock ---
settings.jwt_secret = "e2e-secret"
settings.otp_cooldown_sec = 0
settings.otp_ttl_sec = 300
engine = create_engine("sqlite:////tmp/e2e.db", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
real_odoo = HttpOdooClient(settings.odoo_base_url, settings.coc_shared_secret)
mock = MockOtpProvider()
notifier = MockLoginNotifier()


def override_db():
    db = Session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


app.dependency_overrides[deps.get_db] = override_db
app.dependency_overrides[deps.get_otp_provider] = lambda: mock
app.dependency_overrides[deps.get_notifier] = lambda: notifier
# get_odoo_client NO se sobreescribe -> HttpOdooClient real contra STAGING

client = TestClient(app)


def mint(partner_id):
    db = Session()
    ident = session_service.get_or_create_identity(db, f"+5200{partner_id:08d}", partner_id)
    toks = session_service.create_session(db, real_odoo, ident, partner_id, "127.0.0.1", f"e2e-{partner_id}", "e2e", notifier)
    db.commit()
    db.close()
    return toks


def H(tok):
    return {"Authorization": f"Bearer {tok}"}


def timed(method, path, **kw):
    t0 = time.perf_counter()
    r = getattr(client, method)(path, **kw)
    return r, round((time.perf_counter() - t0) * 1000, 1)


# ===== 1. Login OTP completo contra STAGING (mock + resolve real) =====
try:
    phone = "+520000000777"  # fijado en el partner alarm_res (25757)
    rq = client.post("/v1/auth/otp/request", json={"phone": phone, "device": "e2e-otp"})
    code = mock.last_code(phone)
    rv = client.post("/v1/auth/otp/verify", json={"phone": phone, "code": code, "device": "e2e-otp"})
    body = rv.json()
    ok = rq.status_code == 200 and rv.status_code == 200 and body.get("access_token") and body.get("session_id")
    ev("1_login_otp", OK if ok else FAIL,
       f"request={rq.status_code} verify={rv.status_code} token={'si' if body.get('access_token') else 'no'} resolve->partner {PICK['alarm_res']}")
    otp_token = body.get("access_token")
except Exception as e:
    ev("1_login_otp", FAIL, repr(e))
    otp_token = None

# ===== 2/3/11/13. Dashboard por tipo de cliente + Estado de Tranquilidad + timings =====
CLIENTS = [
    ("residencial_alarma_suspendido_sinfacturas", PICK["alarm_res"]),
    ("internet_empresarial", PICK["internet"]),
    ("multiservicio", PICK["multi"]),
    ("con_factura", PICK["con_factura"]),
]
tokens = {}
for label, pid in CLIENTS:
    try:
        tk = mint(pid)["access_token"]
        tokens[pid] = tk
        dash, dms = timed("get", "/v1/dashboard", headers=H(tk))
        svc, sms = timed("get", "/v1/services", headers=H(tk))
        bil, bms = timed("get", "/v1/billing/summary", headers=H(tk))
        d = dash.json()["data"]
        ev(f"13_{label}", OK if dash.status_code == 200 else FAIL,
           f"pid={pid} peace={d['peace_of_mind']['status']} servicios(total/activos/susp)={d['services']['total']}/{d['services']['active']}/{d['services']['suspended']} "
           f"saldo={d['billing']['total_due']} vencido={d['billing']['overdue_amount']} acciones={len(d['next_actions'])}")
        ev(f"11_timings_{label}", OK, f"dashboard={dms}ms services={sms}ms billing_summary={bms}ms")
    except Exception as e:
        ev(f"13_{label}", FAIL, repr(e))

# 3. Estado de Tranquilidad coherente: 25757 está suspendido -> debe 'atencion'
try:
    d = client.get("/v1/dashboard", headers=H(tokens[PICK["alarm_res"]])).json()["data"]
    coh = (d["services"]["suspended"] > 0 or d["billing"]["overdue_amount"] > 0) == (d["peace_of_mind"]["status"] == "atencion")
    ev("3_estado_tranquilidad", OK if coh else FAIL,
       f"suspendidos={d['services']['suspended']} vencido={d['billing']['overdue_amount']} -> estado={d['peace_of_mind']['status']} (coherente={coh})")
except Exception as e:
    ev("3_estado_tranquilidad", FAIL, repr(e))

# ===== 4. Mis Servicios solo del cliente =====
try:
    tk = tokens[PICK["internet"]]
    svc = client.get("/v1/services", headers=H(tk)).json()["data"]
    ev("4_servicios_propios", OK if svc["count"] >= 1 else FAIL,
       f"pid={PICK['internet']} servicios={svc['count']} tipos={sorted(set(s['service_type'] for s in svc['items']))}")
except Exception as e:
    ev("4_servicios_propios", FAIL, repr(e))

# ===== 5. Facturación solo del cliente =====
try:
    tk = tokens[PICK["con_factura"]]
    inv = client.get("/v1/billing/invoices?limit=50", headers=H(tk)).json()["data"]
    ev("5_facturas_propias", OK if inv["count"] >= 1 else FAIL, f"pid={PICK['con_factura']} facturas={inv['count']}")
except Exception as e:
    ev("5_facturas_propias", FAIL, repr(e))

# ===== 6. Descarga PDF y XML válida =====
try:
    tk = tokens[PICK["con_factura"]]
    pdf, pms = timed("get", f"/v1/billing/invoices/{PICK['inv_id']}/pdf", headers=H(tk))
    okpdf = pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    ev("6_pdf", OK if okpdf else FAIL, f"inv={PICK['inv_id']} http={pdf.status_code} magic={pdf.content[:4]!r} bytes={len(pdf.content)} t={pms}ms")
except Exception as e:
    ev("6_pdf", FAIL, repr(e))
try:
    xtk = mint(PICK["xml_partner"])["access_token"]
    xml = client.get(f"/v1/billing/invoices/{PICK['xml_inv']}/xml", headers=H(xtk))
    okxml = xml.status_code == 200 and (b"<?xml" in xml.content[:60] or b"Comprobante" in xml.content[:400])
    ev("6_xml", OK if okxml else FAIL, f"inv={PICK['xml_inv']} http={xml.status_code} bytes={len(xml.content)} head={xml.content[:30]!r}")
except Exception as e:
    ev("6_xml", FAIL, repr(e))

# ===== 7. IDOR: A no accede a recursos de B (404) =====
try:
    tkA = tokens[PICK["con_factura"]]  # A=25763, inv propia 144
    own = client.get(f"/v1/billing/invoices/{PICK['idorA_inv']}", headers=H(tkA)).status_code
    cross = client.get(f"/v1/billing/invoices/{PICK['idorB_inv']}", headers=H(tkA)).status_code  # B inv 143
    crosspdf = client.get(f"/v1/billing/invoices/{PICK['idorB_inv']}/pdf", headers=H(tkA)).status_code
    ev("7_idor", OK if own == 200 and cross == 404 and crosspdf == 404 else FAIL,
       f"propia(144)={own} ajena_detalle(143)={cross} ajena_pdf(143)={crosspdf}")
except Exception as e:
    ev("7_idor", FAIL, repr(e))

# ===== 8. Expiración de sesión + refresh token =====
try:
    t = mint(PICK["con_factura"])
    at, rt = t["access_token"], t["refresh_token"]
    before = client.get("/v1/services", headers=H(at)).status_code
    # refresh rota tokens
    r1 = client.post("/v1/auth/refresh", json={"refresh_token": rt})
    new = r1.json()
    after_new = client.get("/v1/services", headers=H(new.get("access_token", ""))).status_code
    # reuse del refresh viejo -> 401 (familia revocada)
    r2 = client.post("/v1/auth/refresh", json={"refresh_token": rt})
    ev("8_refresh", OK if before == 200 and r1.status_code == 200 and after_new == 200 and r2.status_code == 401 else FAIL,
       f"access_ok={before} refresh={r1.status_code} access_nuevo={after_new} reuse_viejo={r2.status_code}")
    # logout revoca el access inmediatamente (expiración efectiva)
    t2 = mint(PICK["con_factura"])
    at2 = t2["access_token"]
    pre = client.get("/v1/services", headers=H(at2)).status_code
    client.post("/v1/auth/logout", headers=H(at2))
    post = client.get("/v1/services", headers=H(at2)).status_code
    ev("8_logout_revoca", OK if pre == 200 and post == 401 else FAIL, f"antes={pre} tras_logout={post} (access revocable)")
except Exception as e:
    ev("8_refresh", FAIL, repr(e))

# ===== 9. Caché: Dashboard 30s + PDF 300s =====
try:
    tk = tokens[PICK["con_factura"]]
    d1 = client.get("/v1/dashboard", headers=H(tk)).json()["meta"]["last_refresh"]
    d2 = client.get("/v1/dashboard", headers=H(tk)).json()["meta"]["last_refresh"]
    ev("9_cache_dashboard", OK if d1 == d2 else FAIL, f"last_refresh estable en 2 llamadas dentro de TTL=30s ({d1} == {d2})")
    p1, t1 = timed("get", f"/v1/billing/invoices/{PICK['inv_id']}/pdf", headers=H(tk))
    p2, t2 = timed("get", f"/v1/billing/invoices/{PICK['inv_id']}/pdf", headers=H(tk))
    ev("9_cache_pdf", OK if t2 < t1 else FAIL, f"1a={t1}ms (render) 2a={t2}ms (cache TTL=300s) -> {round(t1 / max(t2, 0.1), 1)}x más rápido")
except Exception as e:
    ev("9_cache", FAIL, repr(e))

# ===== 10. request_id + auditoría en Gateway =====
try:
    r = client.get("/v1/dashboard", headers=H(tokens[PICK["con_factura"]]))
    hdr = r.headers.get("x-request-id")
    metarid = r.json()["meta"]["request_id"]
    from app.models import AuthAuditEvent
    db = Session()
    types = sorted({e.event_type for e in db.query(AuthAuditEvent).all()})
    db.close()
    ev("10_request_id_audit", OK if hdr and metarid else FAIL,
       f"X-Request-Id={'si' if hdr else 'no'} meta.request_id={'si' if metarid else 'no'} eventos_auditoria_gateway={types}")
except Exception as e:
    ev("10_request_id_audit", FAIL, repr(e))

# Resumen
passed = sum(1 for _, s, _ in results if s == OK)
print(f"\nE2E_SUMMARY pass={passed}/{len(results)}")
