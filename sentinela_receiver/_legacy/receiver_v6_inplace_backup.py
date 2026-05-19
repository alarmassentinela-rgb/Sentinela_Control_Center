import socket
import xmlrpc.client
import threading
import re
import time
import logging
from datetime import datetime

# Configurar Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("receiver_fast.log", mode='a'), logging.StreamHandler()]
)

socket.setdefaulttimeout(10)

# CONFIGURACION ODOO
ODOO_URL = "http://192.168.3.2:8070"
ODOO_DB = "Sentinela_V18"
ODOO_USER = "api_user"
ODOO_PASS = "SentinelaBot2026!"
LISTEN_PORT = 10001

def get_odoo_connection():
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, [])
        if uid:
            models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
            return uid, models
        return None, None
    except: return None, None

def heartbeat_loop():
    logging.info("[SYSTEM] Iniciando Heartbeat...")
    while True:
        try:
            uid, models = get_odoo_connection()
            if uid:
                models.execute_kw(ODOO_DB, uid, ODOO_PASS,
                                  'sentinela.receiver.status', 'update_heartbeat', [])
        except Exception as e:
            logging.error(f"[ERROR HEARTBEAT] {e}")
        time.sleep(10)

def parse_contact_id(data):
    pattern = r"\[(\w{1,4})\s*(\w{2})\s*([E|R])(\w{3})\s*(\w{2})\s*(\w{3})\]"
    match = re.search(pattern, data)
    if match:
        return {
            'account': match.group(1).zfill(4), 'qualifier': match.group(3),
            'code': match.group(4), 'partition': match.group(5), 'zone': match.group(6)
        }
    return None

def handle_client(conn, addr):
    try:
        data = conn.recv(1024).decode('utf-8', errors='ignore')
        if data:
            logging.info(f"[RAW] {data.strip()}")
            cid = parse_contact_id(data)
            if cid:
                conn.send(b'\x06') # ACK inmediato para liberar el panel
                # PROCESAR EN ODOO (UNA SOLA LLAMADA MAESTRA)
                process_fast(cid, data)
    except: pass
    finally: conn.close()

def process_fast(cid, raw_data):
    try:
        uid, models = get_odoo_connection()
        if not uid: return
        
        # LLAMADA ÚNICA DE ALTA VELOCIDAD
        models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'sentinela.alarm.event', 'process_signal_from_receptor', [{
            'account': cid['account'],
            'code': cid['code'],
            'zone': cid['zone'],
            'qualifier': cid['qualifier'],
            'raw_data': raw_data
        }])
        logging.info(f"[OK] Señal {cid['account']}-{cid['code']} procesada en Odoo.")
    except Exception as e:
        logging.error(f"[ERROR] RPC Falló: {e}")

def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', LISTEN_PORT))
    s.listen(10)
    logging.info(f"[*] Receptor FAST iniciado en puerto {LISTEN_PORT}")
    while True:
        try:
            c, a = s.accept()
            threading.Thread(target=handle_client, args=(c, a), daemon=True).start()
        except: pass

if __name__ == "__main__":
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    start_server()
