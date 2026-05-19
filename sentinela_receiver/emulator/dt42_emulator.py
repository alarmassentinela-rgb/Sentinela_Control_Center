#!/usr/bin/env python3
"""
Emulador de paneles DT42 / Surgard Contact ID para Sentinela.

Modos de uso:

    Interactivo (menú):
        python3 dt42_emulator.py

    One-shot por CLI:
        python3 dt42_emulator.py --account 1025 --code 130
        python3 dt42_emulator.py --account 1025 --code 401 --qualifier R --zone 003
        python3 dt42_emulator.py --account 1025 --code 130 --target 192.168.3.2:10002

    Modo automático (varias señales seguidas):
        python3 dt42_emulator.py --account 1025 --code 130 --auto --count 5 --interval 2

Formato de trama Surgard:
    [AAAA 18 QEEE PP ZZZ]
        AAAA = cuenta
        18   = prefijo MCDI/Surgard
        Q    = E (new) | R (restore)
        EEE  = código Contact ID (3 dígitos)
        PP   = partición (default 01)
        ZZZ  = zona / usuario (3 dígitos)
"""
import argparse
import socket
import sys
import time

DEFAULT_HOST = "192.168.3.2"
DEFAULT_PORT = 10001  # prod; LAB usa 10002
DEFAULT_ACCOUNT = "1025"

SIGNALS = {
    "1": {"code": "130", "desc": "Robo (Burglary)", "qualifier": "E"},
    "2": {"code": "110", "desc": "Fuego (Fire)", "qualifier": "E"},
    "3": {"code": "120", "desc": "Pánico (Panic)", "qualifier": "E"},
    "4": {"code": "100", "desc": "Médica (Medical)", "qualifier": "E"},
    "5": {"code": "401", "desc": "Apertura (Open/Disarm)", "qualifier": "E"},
    "6": {"code": "402", "desc": "Cierre (Close/Arm)", "qualifier": "E"},
    "7": {"code": "602", "desc": "Test Periódico", "qualifier": "E"},
    "8": {"code": "301", "desc": "Fallo AC (Corte Luz)", "qualifier": "E"},
    "9": {"code": "302", "desc": "Batería Baja", "qualifier": "E"},
}


def parse_target(value):
    """Acepta '192.168.3.2', '192.168.3.2:10002' o 'host:port'."""
    if not value:
        return DEFAULT_HOST, DEFAULT_PORT
    if ":" in value:
        host, port_str = value.rsplit(":", 1)
        return host, int(port_str)
    return value, DEFAULT_PORT


def send_signal(host, port, account, code, qualifier="E", partition="01", zone="001",
                timeout=5, quiet=False):
    msg = f"[{account} 18 {qualifier}{code} {partition} {zone}]"
    if not quiet:
        print(f"-> {host}:{port} | {msg}")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            sock.connect((host, port))
            sock.sendall(msg.encode("utf-8"))
            try:
                response = sock.recv(1024)
            except socket.timeout:
                response = b""
        if response == b"\x06":
            if not quiet:
                print("   ACK recibido")
            return True
        if not quiet:
            print(f"   sin ACK (respuesta: {response!r})")
        return True  # el receiver puede no devolver ACK pero igual procesar
    except ConnectionRefusedError:
        print(f"   ERROR: connection refused — ¿receiver corriendo en {host}:{port}?",
              file=sys.stderr)
        return False
    except OSError as e:
        print(f"   ERROR: {e}", file=sys.stderr)
        return False


def run_auto(host, port, account, code, qualifier, zone, count, interval):
    ok = 0
    for i in range(count):
        if send_signal(host, port, account, code, qualifier, zone=zone):
            ok += 1
        if i < count - 1:
            time.sleep(interval)
    print(f"\nTotal: {ok}/{count} señales enviadas.")
    return ok == count


def run_interactive(host, port):
    print("==========================================")
    print("   EMULADOR DE SEÑALES DE ALARMA (DT42)   ")
    print(f"   Target: {host}:{port}")
    print("==========================================")
    current_account = DEFAULT_ACCOUNT
    while True:
        print(f"\n--- Cuenta actual: {current_account} ---")
        for key, val in SIGNALS.items():
            print(f" {key}. {val['desc']} (Código {val['code']})")
        print(" A. Cambiar cuenta")
        print(" M. Señal manual")
        print(" T. Cambiar target (host:port)")
        print(" Q. Salir")
        choice = input("\nOpción > ").strip().upper()
        if choice == "Q":
            break
        elif choice == "A":
            current_account = input("Nuevo número de cuenta: ").strip() or current_account
        elif choice == "T":
            new_target = input(f"Nuevo target [{host}:{port}]: ").strip()
            if new_target:
                host, port = parse_target(new_target)
        elif choice == "M":
            code = input("Código (ej. 130): ").strip()
            qual = (input("Calificador (E/R) [E]: ").strip() or "E").upper()
            zone = input("Zona/usuario [001]: ").strip() or "001"
            send_signal(host, port, current_account, code, qual, zone=zone)
        elif choice in SIGNALS:
            sig = SIGNALS[choice]
            zone = input(f"Zona para {sig['desc']} [001]: ").strip() or "001"
            send_signal(host, port, current_account, sig["code"], sig["qualifier"], zone=zone)
        else:
            print("Opción no válida.")


def main():
    parser = argparse.ArgumentParser(description="Emulador DT42 Contact ID para Sentinela")
    parser.add_argument("--target", help="host[:port], ej. 192.168.3.2:10002")
    parser.add_argument("--account", help="número de cuenta (4 dígitos)")
    parser.add_argument("--code", help="código Contact ID (3 dígitos)")
    parser.add_argument("--qualifier", default="E", choices=["E", "R"],
                        help="E=new (default), R=restore")
    parser.add_argument("--zone", default="001", help="zona / usuario (default 001)")
    parser.add_argument("--partition", default="01", help="partición (default 01)")
    parser.add_argument("--auto", action="store_true",
                        help="modo automático: envía --count señales con --interval segundos")
    parser.add_argument("--count", type=int, default=1, help="cantidad en modo --auto (default 1)")
    parser.add_argument("--interval", type=float, default=1.0,
                        help="segundos entre envíos en --auto (default 1.0)")
    parser.add_argument("--quiet", action="store_true", help="no imprime cada envío")
    args = parser.parse_args()

    host, port = parse_target(args.target)

    if not args.account and not args.code:
        run_interactive(host, port)
        return 0

    if not (args.account and args.code):
        parser.error("--account y --code deben ir juntos (o ninguno para modo interactivo)")

    if args.auto:
        ok = run_auto(host, port, args.account, args.code, args.qualifier,
                      args.zone, args.count, args.interval)
        return 0 if ok else 1
    ok = send_signal(host, port, args.account, args.code, args.qualifier,
                     args.partition, args.zone, quiet=args.quiet)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
