import os
import socket
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- CONFIGURATION ---
MIKROTIK_IP = '192.168.3.3'
MIKROTIK_USER = 'admin'
MIKROTIK_PASS = ''
RECEIVER_LOG = 'receiver_new.log'

class MikrotikMini:
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password

    def _encode_word(self, word):
        word = word.encode('utf-8')
        length = len(word)
        if length < 0x80: res = bytes([length])
        elif length < 0x4000: res = bytes([length >> 8 | 0x80, length & 0xFF])
        else: res = bytes([length])
        return res + word

    def _read_word(self, sock):
        try:
            b = sock.recv(1)
            if not b: return None
            length = b[0]
            if length == 0: return ""
            if length & 0x80:
                b2 = sock.recv(1)
                length = ((length & 0x7F) << 8) + b2[0]
            return sock.recv(length).decode('utf-8', errors='ignore')
        except: return None

    def get_status(self):
        try:
            sock = socket.create_connection((self.host, 8728), timeout=2)
            for w in ['/login', '=name=' + self.user, '=password=' + self.password]:
                sock.sendall(self._encode_word(w))
            sock.sendall(b'\x00')
            while True:
                w = self._read_word(sock)
                if w is None or w == "!done": break
            for w in ['/ppp/active/print']:
                sock.sendall(self._encode_word(w))
            sock.sendall(b'\x00')
            count = 0
            while True:
                w = self._read_word(sock)
                if w is None or w == "!done": break
                if w == "!re": count += 1
            sock.close()
            return {"online": True, "count": count}
        except:
            return {"online": False, "count": 0}

def get_alarm_data():
    if not os.path.exists(RECEIVER_LOG):
        return {"status": "LOG NO ENCONTRADO", "signals": []}
    try:
        with open(RECEIVER_LOG, 'r') as f:
            lines = f.readlines()
            if not lines: return {"status": "VACIO", "signals": []}
            valid_lines = [l for l in lines if " - " in l]
            if not valid_lines: return {"status": "SIN DATOS", "signals": []}
            last_line = valid_lines[-1]
            last_time_str = last_line.split(' - ')[0]
            last_time = datetime.strptime(last_time_str, '%Y-%m-%d %H:%M:%S,%f')
            diff = (datetime.now() - last_time).total_seconds()
            status = "ACTIVO" if diff < 600 else "STALE (REVISAR)"
            signals = [l.split("[RAW] ")[-1].strip() for l in reversed(lines) if "[RAW]" in l][:10]
            return {"status": status, "last_activity": last_time_str, "signals": signals}
    except:
        return {"status": "ERROR DE PARSEO", "signals": []}

class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        mt = MikrotikMini(MIKROTIK_IP, MIKROTIK_USER, MIKROTIK_PASS)
        isp = mt.get_status()
        alarms = get_alarm_data()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Sentinela Dashboard</title>
            <meta http-equiv="refresh" content="10">
            <style>
                body {{ font-family: sans-serif; background: #1a1a1a; color: #eee; padding: 20px; }}
                .card {{ background: #252525; padding: 20px; border-radius: 8px; margin-bottom: 20px; border-left: 10px solid #444; }}
                .online {{ border-left-color: #2ecc71; }}
                .offline {{ border-left-color: #e74c3c; }}
                .warning {{ border-left-color: #f1c40f; }}
                .stat {{ font-size: 3em; font-weight: bold; color: #3498db; }}
                .signals {{ background: #111; padding: 10px; border-radius: 5px; font-family: monospace; color: #0f0; }}
            </style>
        </head>
        <body>
            <h1>SENTINELA COMMAND CENTER</h1>
            <p>Actualizado: {now}</p>
            
            <div class="card {'online' if isp['online'] else 'offline'}">
                <h2>ISP / MIKROTIK</h2>
                <div class="stat">{isp['count']}</div>
                <p>Sesiones PPPoE Activas</p>
                <p>Estado: {'CONECTADO' if isp['online'] else 'ERROR DE CONEXION'}</p>
            </div>

            <div class="card {'online' if alarms['status'] == 'ACTIVO' else 'warning'}">
                <h2>RECEPTOR DE ALARMAS</h2>
                <p>Estado: {alarms['status']}</p>
                <p>Última actividad: {alarms.get('last_activity', 'N/A')}</p>
                <h3>Últimas Señales:</h3>
                <div class="signals">
                    {'<br>'.join(['> ' + s for s in alarms['signals']]) if alarms['signals'] else 'No hay señales registradas'}
                </div>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode('utf-8'))

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', 8080), DashboardHandler)
    print("Servidor iniciado en el puerto 8080...")
    server.serve_forever()
