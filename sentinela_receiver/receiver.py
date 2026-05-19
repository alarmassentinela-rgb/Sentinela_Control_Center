#!/usr/bin/env python3
"""
Sentinela Alarm Receiver — unified, multi-DB capable.

One process per Odoo DB. Configuration via YAML file passed as first arg:

    python3 receiver.py config_prod.yaml
    python3 receiver.py config_lab.yaml

Responsibilities:
- Listen TCP on configured port
- Persist raw signal bytes always (even on parse failure) via Odoo XML-RPC
- Parse Contact ID and dispatch to alarm.event.process_signal_from_receptor
- Heartbeat loop independent of incoming signals
"""
import socket
import sys
import threading
import time
import logging
import xmlrpc.client
from pathlib import Path

import yaml

from parsers import get_parser

CONFIG = {}
ODOO = {}


def load_config(path):
    with open(path) as f:
        cfg = yaml.safe_load(f)
    required = ['odoo_url', 'odoo_db', 'odoo_user', 'odoo_password',
                'listen_port', 'parser', 'log_file', 'instance_name']
    missing = [k for k in required if k not in cfg]
    if missing:
        raise ValueError(f"Config missing keys: {missing}")
    return cfg


def setup_logging(cfg):
    logging.basicConfig(
        level=getattr(logging, cfg.get('log_level', 'INFO')),
        format=f"%(asctime)s [{cfg['instance_name']}] %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(cfg['log_file'], mode='a'),
            logging.StreamHandler(),
        ],
    )


def get_odoo_connection():
    try:
        common = xmlrpc.client.ServerProxy(f"{CONFIG['odoo_url']}/xmlrpc/2/common")
        uid = common.authenticate(CONFIG['odoo_db'], CONFIG['odoo_user'],
                                  CONFIG['odoo_password'], {})
        if not uid:
            logging.error("Odoo auth failed: bad credentials or DB")
            return None, None
        models = xmlrpc.client.ServerProxy(f"{CONFIG['odoo_url']}/xmlrpc/2/object")
        return uid, models
    except Exception as e:
        logging.error(f"Odoo connection error: {e}")
        return None, None


def heartbeat_loop():
    logging.info("Heartbeat thread starting")
    interval = CONFIG.get('heartbeat_interval_seconds', 10)
    while True:
        uid, models = get_odoo_connection()
        if uid:
            try:
                models.execute_kw(
                    CONFIG['odoo_db'], uid, CONFIG['odoo_password'],
                    'sentinela.receiver.status', 'update_heartbeat', []
                )
            except Exception as e:
                logging.error(f"Heartbeat call failed: {e}")
        time.sleep(interval)


def dispatch_to_odoo(parsed, raw_bytes):
    """Call into Odoo to create signal + event."""
    uid, models = get_odoo_connection()
    if not uid:
        logging.error(f"No Odoo connection — signal dropped: {parsed}")
        return False
    try:
        models.execute_kw(
            CONFIG['odoo_db'], uid, CONFIG['odoo_password'],
            'sentinela.alarm.event', 'process_signal_from_receptor',
            [{
                'account': parsed['account'],
                'code': parsed['code'],
                'zone': parsed['zone'],
                'qualifier': parsed['qualifier'],
                'raw_data': raw_bytes.hex(),
            }]
        )
        logging.info(f"OK signal account={parsed['account']} code={parsed['code']} zone={parsed['zone']}")
        return True
    except Exception as e:
        logging.error(f"RPC dispatch failed: {e}")
        return False


def handle_client(conn, addr, parser):
    try:
        conn.settimeout(CONFIG.get('socket_timeout_seconds', 10))
        data = conn.recv(1024)
        if not data:
            return
        logging.debug(f"RAW from {addr[0]}: {data.hex()} ({len(data)} bytes)")

        parsed = parser.parse(data)
        if not parsed:
            logging.warning(f"Unparseable from {addr[0]}: {data!r}")
            return

        conn.send(b'\x06')  # ACK immediately to free the panel
        dispatch_to_odoo(parsed, data)
    except Exception as e:
        logging.error(f"handle_client error from {addr}: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


def start_server():
    parser = get_parser(CONFIG['parser'])
    bind_ip = CONFIG.get('bind_ip', '0.0.0.0')
    port = CONFIG['listen_port']

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((bind_ip, port))
    s.listen(10)
    logging.info(f"Receiver listening on {bind_ip}:{port} → {CONFIG['odoo_db']}")

    while True:
        try:
            c, a = s.accept()
            threading.Thread(target=handle_client, args=(c, a, parser),
                             daemon=True).start()
        except Exception as e:
            logging.error(f"accept() error: {e}")


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <config.yaml>", file=sys.stderr)
        sys.exit(2)

    config_path = Path(sys.argv[1]).resolve()
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        sys.exit(2)

    global CONFIG
    CONFIG = load_config(config_path)
    setup_logging(CONFIG)

    logging.info(f"Starting receiver, config={config_path}")

    threading.Thread(target=heartbeat_loop, daemon=True).start()
    start_server()


if __name__ == '__main__':
    main()
