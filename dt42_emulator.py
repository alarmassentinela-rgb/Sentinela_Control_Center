import socket
import time
import sys

# CONFIGURACIÓN POR DEFECTO
DEFAULT_IP = "192.168.3.2"  # IP del Servidor Sentinela
DEFAULT_PORT = 10001
DEFAULT_ACCOUNT = "1025"

# CÓDIGOS CONTACT ID COMUNES
SIGNALS = {
    "1": {"code": "130", "desc": "Robo (Burglary)", "qualifier": "E"},
    "2": {"code": "110", "desc": "Fuego (Fire)", "qualifier": "E"},
    "3": {"code": "120", "desc": "Pánico (Panic)", "qualifier": "E"},
    "4": {"code": "100", "desc": "Médica (Medical)", "qualifier": "E"},
    "5": {"code": "401", "desc": "Apertura (Open/Disarm)", "qualifier": "E"}, # A veces es R
    "6": {"code": "402", "desc": "Cierre (Close/Arm)", "qualifier": "E"},     # A veces es R
    "7": {"code": "602", "desc": "Test Periódico", "qualifier": "E"},
    "8": {"code": "301", "desc": "Fallo AC (Corte Luz)", "qualifier": "E"},
    "9": {"code": "302", "desc": "Batería Baja", "qualifier": "E"},
}

def send_signal(ip, port, account, code, qualifier="E", partition="01", zone="001"):
    """
    Construye y envía la trama simulando DT42 / Surgard
    Formato: [AAAA 18 QEEE PP ZZZ]
    """
    # Construcción de la trama
    # AAAA: Cuenta
    # 18: Prefijo común MCDI/Surgard
    # Q: Qualifier (E=New, R=Restore)
    # EEE: Event Code
    # PP: Partition
    # ZZZ: Zone/User
    
    msg = f"[{account} 18 {qualifier}{code} {partition} {zone}]"
    
    print(f"\n\U0001f6A8 Enviando trama: {msg} a {ip}:{port} ...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5) # 5 segundos timeout
        sock.connect((ip, port))
        
        # Enviar datos
        sock.sendall(msg.encode('utf-8'))
        
        # Esperar ACK (0x06)
        response = sock.recv(1024)
        
        if response == b'\x06':
            print("\U0001f603 ACK Recibido (La central confirmó recepción).")
        else:
            print(f"\U0001f940 Respuesta desconocida: {response}")
            
        sock.close()
        return True
    except ConnectionRefusedError:
        print("\U0001f603 Error: No se pudo conectar. ¿El receiver.py está corriendo?")
        return False
    except socket.timeout:
        print("\U0001f603 Error: Timeout esperando respuesta (ACK).")
        return False
    except Exception as e:
        print(f"\U0001f603 Error inesperado: {e}")
        return False

def main():
    print("==========================================")
    print("   EMULADOR DE SEÑALES DE ALARMA (DT42)   ")
    print("==========================================")
    
    target_ip = input(f"IP Servidor [{DEFAULT_IP}]: ") or DEFAULT_IP
    
    try:
        port_input = input(f"Puerto [{DEFAULT_PORT}]: ")
        target_port = int(port_input) if port_input else DEFAULT_PORT
    except ValueError:
        print("Puerto inválido, usando default.")
        target_port = DEFAULT_PORT

    current_account = DEFAULT_ACCOUNT

    while True:
        print("\n------------------------------------------")
        print(f"Cuenta Actual: {current_account}")
        print("------------------------------------------")
        print("SELECCIONE SEÑAL A ENVIAR:")
        for key, val in SIGNALS.items():
            print(f" {key}. {val['desc']} (Código {val['code']})")
        print(" A. Cambiar Número de Cuenta")
        print(" M. Señal Manual (Personalizada)")
        print(" Q. Salir")
        
        choice = input("\nOpción > ").upper()
        
        if choice == 'Q':
            break
        elif choice == 'A':
            current_account = input("Nuevo Número de Cuenta (4 dígitos): ")
        elif choice == 'M':
            code = input("Código (Ej. 130): ")
            qual = input("Calificador (E/R) [E]: ") or "E"
            zone = input("Zona/Usuario (001): ") or "001"
            send_signal(target_ip, target_port, current_account, code, qual, zone=zone)
        elif choice in SIGNALS:
            sig = SIGNALS[choice]
            zone = input(f"Zona para {sig['desc']} [001]: ") or "001"
            send_signal(target_ip, target_port, current_account, sig['code'], sig['qualifier'], zone=zone)
        else:
            print("Opción no válida.")

if __name__ == "__main__":
    main()
