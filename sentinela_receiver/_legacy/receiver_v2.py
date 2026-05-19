import socket
import requests
import json
import threading
import re

# CONFIGURACION
LISTEN_PORT = 10001
# IMPORTANTE: Puerto 8070 (Odoo Externo) o puerto interno docker
ODOO_URL = "http://localhost:8070/api/monitoring/signal"

def parse_contact_id(data):
    pattern = r"\[(\w{4})\s*(\w{2})\s*([E|R])(\w{3})\s*(\w{2})\s*(\w{3})\]"
    match = re.search(pattern, data)
    if match:
        return {
            'account': match.group(1),
            'qualifier': match.group(3),
            'code': match.group(4),
            'partition': match.group(5),
            'zone_user': match.group(6)
        }
    return None

def handle_client(conn, addr):
    print(f"[RECEPTOR] Conexión desde {addr}")
    try:
        while True:
            data = conn.recv(1024).decode('utf-8')
            if not data: break
            print(f"[DATOS RAW] {data}")
            signal_data = parse_contact_id(data)
            
            if signal_data:
                conn.send(b'\x06') # ACK
                print(f"[PROCESANDO] Enviando a Odoo: {signal_data}")
                try:
                    headers = {'Content-Type': 'application/json'}
                    payload = {"jsonrpc": "2.0", "method": "call", "params": signal_data}
                    response = requests.post(ODOO_URL, headers=headers, data=json.dumps(payload), timeout=5)
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
    print(f"[*] RECEPTOR SENTINELA (V2) escuchando en puerto {LISTEN_PORT}...")
    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    start_server()
