import socket
import xmlrpc.client
import threading
import re
import time

# CONFIGURACION ODOO (XML-RPC)
ODOO_URL = "http://localhost:8070"
ODOO_DB = "Sentinela_V18"
ODOO_USER = "api_user"
ODOO_PASS = "admin"  # CAMBIAR SI ES DIFERENTE

LISTEN_PORT = 10001

def get_odoo_connection():
    try:
        common = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/common')
        uid = common.authenticate(ODOO_DB, ODOO_USER, ODOO_PASS, {})
        if uid:
            models = xmlrpc.client.ServerProxy(f'{ODOO_URL}/xmlrpc/2/object')
            return uid, models
        return None, None
    except Exception as e:
        print(f"[ERROR CONEXION ODOO] {e}")
        return None, None

def parse_contact_id(data):
    # Soporte para formatos variados
    # [1234 18 E130 01 001]
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
    print(f"[RECEPTOR] Conexión: {addr}")
    try:
        while True:
            data = conn.recv(1024).decode('utf-8', errors='ignore')
            if not data: break
            print(f"[RAW] {data.strip()}")
            
            cid = parse_contact_id(data)
            if cid:
                conn.send(b'\x06') # ACK
                
                # Conectar a Odoo
                uid, models = get_odoo_connection()
                if not uid:
                    print("[ERROR] Fallo Login Odoo (Revise User/Pass)")
                    continue

                # Buscar Dispositivo
                print(f"[ODOO] Buscando dispositivo cuenta {cid['account']}...")
                device_ids = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
                    'sentinela.monitoring.device', 'search',
                    [[['account_number', '=', cid['account']]]])
                
                vals = {
                    'signal_type': 'alarm', # Logica simple por ahora
                    'priority': 'medium',
                    'description': f"Evento {cid['qualifier']}{cid['code']} Zona {cid['zone']}",
                    'raw_data': data,
                    'received_date': time.strftime('%Y-%m-%d %H:%M:%S'),
                }

                if device_ids:
                    vals['device_id'] = device_ids[0]
                    print(f"[ODOO] Dispositivo encontrado: ID {device_ids[0]}")
                else:
                    print(f"[ODOO] CUENTA DESCONOCIDA: {cid['account']} -> Creando dispositivo temporal...")
                    # Crear dispositivo al vuelo
                    new_device_id = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
                        'sentinela.monitoring.device', 'create', [{
                            'name': f"Auto-Created {cid['account']}",
                            'account_number': cid['account'],
                            'device_id': cid['account'], 
                            'partner_id': 1, 
                            'status': 'offline',
                            'device_type': 'control_panel', # OBLIGATORIO
                            'protocol': 'contact_id'        # OBLIGATORIO
                        }])
                    vals['device_id'] = new_device_id
                    vals['description'] = f"[NUEVO DISPOSITIVO] " + vals['description']
                    vals['priority'] = 'high'

                # Crear Señal
                signal_id = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
                    'sentinela.alarm.signal', 'create', [vals])
                
                print(f"[EXITO] Señal creada en Odoo: ID {signal_id}")

                # --- NUEVO: CREAR EVENTO AUTOMÁTICO ---
                print(f"[ODOO] Creando Evento Activo para la señal {signal_id}...")
                event_vals = {
                    'name': f"Alarma {cid['account']} - {cid['code']}",
                    'event_type': vals['signal_type'] if vals['signal_type'] != 'alarm' else 'burglary',
                    'device_id': vals.get('device_id'),
                    'priority': vals['priority'],
                    'description': vals['description'],
                    'start_date': vals['received_date'],
                    'status': 'active' # Para que aparezca en "Eventos Activos"
                }
                
                event_id = models.execute_kw(ODOO_DB, uid, ODOO_PASS,
                    'sentinela.alarm.event', 'create', [event_vals])
                
                # Vincular la señal al evento (opcional pero recomendado)
                models.execute_kw(ODOO_DB, uid, ODOO_PASS,
                    'sentinela.alarm.signal', 'write', [[signal_id], {'alarm_event_id': event_id}])
                
                print(f"[EXITO] Evento Activo creado: ID {event_id}")
                
            else:
                print("[ERROR] Trama no reconocida")
                
    except Exception as e:
        print(f"[ERROR SOCKET] {e}")
    finally:
        conn.close()

def start_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', LISTEN_PORT))
    s.listen(5)
    print(f"[*] RECEPTOR SENTINELA (XML-RPC) Port {LISTEN_PORT}")
    while True:
        c, a = s.accept()
        threading.Thread(target=handle_client, args=(c, a)).start()

if __name__ == "__main__":
    start_server()
