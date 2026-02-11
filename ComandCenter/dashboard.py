import os
import sys
import time
import socket
import binascii
import re
from datetime import datetime

# --- CONFIGURATION ---
MIKROTIK_IP = '192.168.3.3'
MIKROTIK_USER = 'admin'
MIKROTIK_PASS = ''
RECEIVER_LOG = 'receiver_new.log'
REFRESH_RATE = 5 # seconds

class MikrotikMini:
    """Minimalistic Mikrotik API Client using raw sockets"""
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password
        self.sock = None

    def _encode_word(self, word):
        word = word.encode('utf-8')
        length = len(word)
        if length < 0x80:
            res = bytes([length])
        elif length < 0x4000:
            res = bytes([length >> 8 | 0x80, length & 0xFF])
        else:
            res = bytes([length]) 
        return res + word

    def _read_word(self):
        try:
            b = self.sock.recv(1)
            if not b: return None
            length = b[0]
            if length == 0: return ""
            if length & 0x80:
                b2 = self.sock.recv(1)
                length = ((length & 0x7F) << 8) + b2[0]
            return self.sock.recv(length).decode('utf-8', errors='ignore')
        except:
            return None

    def connect(self):
        try:
            self.sock = socket.create_connection((self.host, 8728), timeout=3)
            self.send_command(['/login', '=name=' + self.user, '=password=' + self.password])
            res = self.read_response()
            return True
        except:
            return False

    def send_command(self, cmd):
        for word in cmd:
            self.sock.sendall(self._encode_word(word))
        self.sock.sendall(b'\x00')

    def read_response(self):
        replies = []
        while True:
            word = self._read_word()
            if word is None or word == "!done":
                break
            replies.append(word)
        return replies

    def get_active_pppoe(self):
        try:
            self.send_command(['/ppp/active/print'])
            raw = self.read_response()
            count = 0
            for r in raw:
                if r == "!re": count += 1
            return count
        except:
            return "ERR"

def get_receiver_status():
    if not os.path.exists(RECEIVER_LOG):
        return "LOG NOT FOUND", []
    
    try:
        with open(RECEIVER_LOG, 'r') as f:
            lines = f.readlines()
            if not lines:
                return "EMPTY LOG", []
            
            last_lines = [l for l in lines if " - " in l]
            if not last_lines: return "NO DATA", []
            
            last_line = last_lines[-1]
            last_time_str = last_line.split(' - ')[0]
            try:
                last_time = datetime.strptime(last_time_str, '%Y-%m-%d %H:%M:%S,%f')
                diff = datetime.now() - last_time
                status = "ACTIVE" if diff.total_seconds() < 600 else "STALE"
            except:
                status = "UNKNOWN"
            
            signals = []
            for line in reversed(lines):
                if "[RAW]" in line:
                    signals.append(line.strip().split("[RAW] ")[-1])
                if len(signals) >= 5: break
                
            return f"{status} (Last: {last_time_str})", signals
    except:
        return "PARSE ERROR", []

def main():
    mt = MikrotikMini(MIKROTIK_IP, MIKROTIK_USER, MIKROTIK_PASS)
    
    try:
        while True:
            os.system('clear' if os.name == 'posix' else 'cls')
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            print("="*60)
            print(f" SENTINELA COMMAND CENTER - {now}")
            print("="*60)
            
            print(f"\n[ ISP - MIKROTIK ({MIKROTIK_IP}) ]")
            if mt.connect():
                active = mt.get_active_pppoe()
                print(f" Status: ONLINE")
                print(f" Active PPPoE Sessions: {active}")
            else:
                print(f" Status: OFFLINE / UNREACHABLE")
            
            print(f"\n[ ALARM RECEIVER ]")
            rec_status, signals = get_receiver_status()
            print(f" Status: {rec_status}")
            print(" Recent Signals:")
            if not signals:
                print("  (None found)")
            for s in signals:
                print(f"  > {s}")
            
            print("\n" + "="*60)
            print(" Press Ctrl+C to exit. Refreshing in 5s...")
            time.sleep(REFRESH_RATE)
    except KeyboardInterrupt:
        print("\nExiting Command Center...")

if __name__ == "__main__":
    main()
