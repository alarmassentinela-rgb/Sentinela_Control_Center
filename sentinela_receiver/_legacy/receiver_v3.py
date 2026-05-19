import socket
import requests
import json
import threading
import re

# CONFIGURACION
LISTEN_PORT = 10001
# URL CORREGIDA
ODOO_URL = "http://localhost:8070/api/alarm/signals"

def parse_contact_id(data):
    pattern = r"\[(\w{4})\s*(\w{2})\s*([E|R])(\w{3})\s*(\w{2})\s*(\w{3})\]"
    match = re.search(pattern, data)
    if match:
        return {
            'account': match.group(1),
            'qualifier': match.group(3), # E=Event, R=Restore
            'code': match.group(4),
            'partition': match.group(5),
            'zone_user': match.group(6)
        }
    return None

def map_contact_id_to_odoo(cid_data):
    """Traduce el código Contact ID a lo que espera Odoo"""
    code = cid_data['code']
    signal_type = 'alarm' # Default
    
    # Mapeo simple de códigos comunes
    if code in ['130', '131', '132']: signal_type = 'alarm' # Robo
    elif code in ['110', '111']: signal_type = 'fire' # Fuego
    elif code in ['120', '121']: signal_type = 'panic' # Panico
    elif code in ['100']: signal_type = 'medical' # Medico
    elif code in ['602']: signal_type = 'test' # Test
    
    priority = 'high' if signal_type in ['fire', 'panic'] else 'medium'
    
    return {
        'device_id': cid_data['account'], # Usamos la cuenta como ID de dispositivo
        'signal_type': signal_type,
        'priority': priority,
        'description': f"Evento Contact ID: {cid_data['qualifier']}{code} Zona {cid_data['zone_user']}",
        'create_event': True # Para que Odoo genere el evento automáticamente
    }

def handle_client(conn, addr):
    print(f"[RECEPTOR] Conexión desde {addr}")
    try:
        while True:
            data = conn.recv(1024).decode('utf-8')
            if not data: break
            print(f"[DATOS RAW] {data}")
            
            cid_data = parse_contact_id(data)
            
            if cid_data:
                conn.send(b'\x06') # ACK inmediato
                
                # Traducir para Odoo
                odoo_payload = map_contact_id_to_odoo(cid_data)
                print(f"[PROCESANDO] Enviando a Odoo: {odoo_payload}")
                
                try:
                    headers = {
                        'Content-Type': 'application/json',
                        'Authorization': 'Bearer SENTINELA_TOKEN' # Token dummy por ahora
                    }
                    
                    # NOTA: Odoo JSON-RPC vs HTTP Controllers
                    # El controlador que vimos usa type='json', asi que espera una estructura JSON-RPC
                    # standard: {jsonrpc: 2.0, params: {...}}
                    
                    final_payload = {
                        "jsonrpc": "2.0",
                        "method": "call",
                        "params": odoo_payload
                    }
                    
                    response = requests.post(ODOO_URL, headers=headers, data=json.dumps(final_payload), timeout=5)
                    print(f"[ODOO RESPONSE] {response.status_code} - {response.text}")
                    
                except Exception as e:
                    print(f"[ERROR CONECTANDO A ODOO] {e}")
            else:
                print("[ERROR] Formato incorrecto")
    except Exception as e:
        print(f"[ERROR CLIENTE] {e}")
    finally:
        conn.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', LISTEN_PORT))
    server.listen(10)
    print(f"[*] RECEPTOR SENTINELA (V3 Corrected) escuchando en puerto {LISTEN_PORT}...")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    start_server()
