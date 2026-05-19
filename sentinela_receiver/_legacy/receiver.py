import socket
import xmlrpc.client
import threading
import re
import time
import logging
from datetime import datetime

# Configurar Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("receiver_new.log", mode='w'),
        logging.StreamHandler()
    ]
)

# Timeout Global
socket.setdefaulttimeout(15)

# CONFIGURACION ODOO (XML-RPC)
ODOO_URL = "http://192.168.3.2:8070"
ODOO_DB = "Sentinela_V18"
ODOO_USER = "api_user"
ODOO_PASS = "admin" 

LISTEN_PORT = 10001

def get_odoo_connection():
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, [])
        if uid:
            models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
            return uid, models
        return None, None
    except Exception as e:
        logging.error(f"[ERROR CONEXION ODOO] {e}")
        return None, None

def get_priority_id(models, uid, code, name, level):
    try:
        p_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'sentinela.alarm.priority', 'search', [[['code', '=', code]]])
        if p_ids:
            return p_ids[0]
        
        logging.info(f"[SYSTEM] Creando prioridad: {name}")
        return models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'sentinela.alarm.priority', 'create', [{
            'name': name,
            'code': code,
            'level': level,
            'color_hex': '#FF0000' if level > 5 else '#00FF00'
        }])
    except Exception as e:
        logging.error(f"[ERROR PRIORITY] {e}")
        return False

def heartbeat_loop():
    logging.info("[SYSTEM] Iniciando Heartbeat...")
    while True:
        try:
            uid, models = get_odoo_connection()
            if uid:
                models.execute_kw(ODOO_DB, uid, ODOO_PASS, 'sentinela.receiver.status', 'update_heartbeat', [])
        except Exception as e:
            logging.error(f"[ERROR HEARTBEAT] {e}")
        time.sleep(10)

def parse_contact_id(data):
    pattern = r"\[(\w{4})\s*(\w{2})\s*([E|R])(\w{3})\s*(\w{2})\s*(\w{3})\]"
    match = re.search(pattern, data)
    if match:
        return {
            'account': match.group(1),
            'qualifier': match.group(3),
            'code': match.group(4),
            'partition': match.group(5),
            'zone': match.group(6)
        }
    return None

def handle_client(conn, addr):
    logging.info(f"[RECEPTOR] Conexión entrante: {addr}")
    try:
        conn.settimeout(10) # Timeout para socket de cliente
        while True:
            try:
                data = conn.recv(1024).decode('utf-8', errors='ignore')
                if not data: break
                
                logging.info(f"[RAW] {data.strip()}")
                
                cid = parse_contact_id(data)
                if cid:
                    conn.send(b'\x06') # ACK inmediato
                    
                    # Procesar asincronamente para no bloquear el socket
                    # (Ojo: esto es simple, en prod usar cola de mensajes)
                    try:
                        process_signal(cid, data)
                    except Exception as e:
                        logging.error(f"Error procesando señal en Odoo: {e}")
                    
                else:
                    logging.warning(f"[ERROR] Trama no reconocida: {data}")
            except socket.timeout:
                break # Cliente inactivo, cerrar
                
    except Exception as e:
        logging.error(f"[ERROR SOCKET] {e}")
    finally:
        conn.close()

def process_signal(cid, raw_data):
    """Lógica separada para hablar con Odoo"""
    uid, models = get_odoo_connection()
    if not uid: 
        logging.error("No se pudo conectar a Odoo para guardar la señal")
        return

    # Prioridades
    p_normal = get_priority_id(models, uid, 'NORMAL', 'Normal', 3)
    p_high = get_priority_id(models, uid, 'CRITICA', 'Crítica', 9)

    # Buscar Dispositivo
    device_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
        'sentinela.monitoring.device', 'search',
        [[['account_number', '=', cid['account']]]])
    
    vals = {
        'signal_type': 'alarm',
        'priority_id': p_normal,
        'description': f"Evento {cid['qualifier']}{cid['code']} Zona {cid['zone']}",
        'raw_data': raw_data,
        'received_date': time.strftime('%Y-%m-%d %H:%M:%S'),
    }

    if device_ids:
        vals['device_id'] = device_ids[0]
    else:
        # Auto-crear dispositivo
        new_device_id = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
            'sentinela.monitoring.device', 'create', [{
                'name': f"Auto-Created {cid['account']}",
                'account_number': cid['account'],
                'device_id': cid['account'], 
                'partner_id': 1, 
                'status': 'active',
                'device_type': 'control_panel',
                'protocol': 'contact_id'
            }])
        vals['device_id'] = new_device_id
        vals['priority_id'] = p_high
        vals['description'] = "[NUEVO] " + vals['description']

    # Crear Señal
    signal_id = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
        'sentinela.alarm.signal', 'create', [vals])
    
    # Crear Evento Activo (Ticket)
    event_vals = {
        'name': f"Alarma {cid['account']} - {cid['code']}",
        'event_type': 'burglary', 
        'device_id': vals['device_id'],
        'priority_id': vals['priority_id'],
        'description': vals['description'],
        'start_date': vals['received_date'],
        'status': 'active'
    }
    event_id = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
        'sentinela.alarm.event', 'create', [event_vals])
    
    models.execute_kw(ODOO_DB, uid, ODOO_PASS,
        'sentinela.alarm.signal', 'write', [[signal_id], {'alarm_event_id': event_id}])
    
    logging.info(f"[EXITO] Evento ID {event_id} creado en Odoo.")

def start_server():
    # Iniciar hilo de Heartbeat
    hb_thread = threading.Thread(target=heartbeat_loop)
    hb_thread.daemon = True
    hb_thread.start()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', LISTEN_PORT))
    s.listen(5)
    print(f"[*] RECEPTOR SENTINELA (V6 Heartbeat + Logs) Port {LISTEN_PORT}")
    logging.info(f"[*] Receptor iniciado en puerto {LISTEN_PORT}")
    
    while True:
        try:
            c, a = s.accept()
            threading.Thread(target=handle_client, args=(c, a)).start()
        except Exception as e:
            logging.error(f"Error en accept: {e}")

if __name__ == "__main__":
    start_server()