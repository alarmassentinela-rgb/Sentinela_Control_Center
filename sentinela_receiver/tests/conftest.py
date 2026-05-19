"""
Fixtures compartidos para los tests end-to-end del receiver Sentinela.

Configuración por variables de entorno (todo opcional excepto password):

    SENTINELA_TEST_URL          default http://192.168.3.2:8070
    SENTINELA_TEST_DB           default Sentinela_STAGING
    SENTINELA_TEST_USER         default api_user
    SENTINELA_TEST_PASSWORD     REQUERIDO — sin password los tests se saltan
    SENTINELA_TEST_RECEIVER     default 192.168.3.2:10002 (LAB)
    SENTINELA_TEST_ACCOUNT      default 1025 (cuenta conocida en STAGING)
    SENTINELA_TEST_DEVICE_ID    default 4   (id del device de SENTINELA_TEST_ACCOUNT)

SEGURIDAD: los tests apuntan a LAB (Sentinela_STAGING). Apuntar a PROD requiere
sobrescribir SENTINELA_TEST_DB explícitamente y debería evitarse —
los tests crean signals y eventos.
"""
import os
import socket
import time
import xmlrpc.client

import pytest


@pytest.fixture(scope="session")
def cfg():
    pwd = os.environ.get("SENTINELA_TEST_PASSWORD")
    if not pwd:
        pytest.skip("SENTINELA_TEST_PASSWORD no seteado — saltando tests e2e")
    return {
        "url": os.environ.get("SENTINELA_TEST_URL", "http://192.168.3.2:8070"),
        "db": os.environ.get("SENTINELA_TEST_DB", "Sentinela_STAGING"),
        "user": os.environ.get("SENTINELA_TEST_USER", "api_user"),
        "password": pwd,
        "receiver": os.environ.get("SENTINELA_TEST_RECEIVER", "192.168.3.2:10002"),
        "account": os.environ.get("SENTINELA_TEST_ACCOUNT", "1025"),
        "device_id": int(os.environ.get("SENTINELA_TEST_DEVICE_ID", "4")),
    }


@pytest.fixture(scope="session")
def odoo(cfg):
    common = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/common")
    uid = common.authenticate(cfg["db"], cfg["user"], cfg["password"], {})
    if not uid:
        pytest.fail(f"Auth falló contra {cfg['url']} / {cfg['db']}")
    models = xmlrpc.client.ServerProxy(f"{cfg['url']}/xmlrpc/2/object")

    def call(model, method, args=None, kwargs=None):
        return models.execute_kw(cfg["db"], uid, cfg["password"],
                                  model, method, args or [], kwargs or {})

    return call


@pytest.fixture
def send_trama(cfg):
    """Manda una trama Contact ID al receiver y devuelve True si conectó.
    Espera 1s después para que el receiver procese."""
    host, port_str = cfg["receiver"].split(":")
    port = int(port_str)

    def _send(account, code, qualifier="E", partition="01", zone="001"):
        msg = f"[{account} 18 {qualifier}{code} {partition} {zone}]"
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((host, port))
            s.sendall(msg.encode("utf-8"))
            try:
                s.recv(1024)
            except socket.timeout:
                pass
        time.sleep(1)
        return msg

    return _send


@pytest.fixture
def cleanup_quarantine(odoo):
    """Borra señales de cuarentena de la cuenta dada al terminar el test."""
    accounts_to_clean = []

    def _register(account):
        accounts_to_clean.append(account)

    yield _register

    for account in accounts_to_clean:
        ids = odoo("sentinela.alarm.signal", "search",
                   [[("is_quarantine", "=", True), ("quarantine_account", "=", account)]])
        if ids:
            odoo("sentinela.alarm.signal", "unlink", [ids])


@pytest.fixture
def reset_device(odoo, cfg):
    """Resetea expected_heartbeat_hours y last_communication del device de prueba
    al final del test. Mantiene status=active."""
    yield
    odoo("sentinela.monitoring.device", "write",
         [[cfg["device_id"]], {"expected_heartbeat_hours": 0.0, "status": "active"}])
    # cerrar cualquier evento [AUTO_OFFLINE] abierto del device
    open_ids = odoo("sentinela.alarm.event", "search",
                    [[("device_id", "=", cfg["device_id"]),
                      ("status", "in", ["active", "acknowledged", "in_progress"]),
                      ("description", "like", "[AUTO_OFFLINE]%")]])
    if open_ids:
        odoo("sentinela.alarm.event", "write",
             [open_ids, {"status": "closed", "end_date": False}])
