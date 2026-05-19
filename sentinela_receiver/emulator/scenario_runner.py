#!/usr/bin/env python3
"""
Ejecutor de escenarios YAML contra el receiver Sentinela.

Uso:
    python3 scenario_runner.py scenarios/basic_signals.yaml
    python3 scenario_runner.py scenarios/basic_signals.yaml --target 192.168.3.2:10002

El target del CLI sobrescribe el del YAML (útil para apuntar LAB o PROD sin
editar el escenario).

Formato YAML:

    name: Nombre del escenario
    description: Texto descriptivo opcional
    target:                      # opcional, sobrescribible por --target
      host: 192.168.3.2
      port: 10002
    steps:
      - account: "1025"
        code: "130"
        qualifier: E            # opcional, default E
        zone: "003"             # opcional, default 001
        partition: "01"         # opcional, default 01
        delay_after: 2          # segundos antes del siguiente step
        note: Burglary alarm    # opcional, solo log
"""
import argparse
import sys
import time
from pathlib import Path

import yaml

from dt42_emulator import send_signal, parse_target, DEFAULT_HOST, DEFAULT_PORT


def run_scenario(path, override_target=None):
    with open(path) as f:
        scenario = yaml.safe_load(f)

    name = scenario.get("name", path.stem)
    print(f"=== Escenario: {name} ===")
    if scenario.get("description"):
        print(scenario["description"])

    tgt = scenario.get("target") or {}
    host = tgt.get("host", DEFAULT_HOST)
    port = tgt.get("port", DEFAULT_PORT)
    if override_target:
        host, port = parse_target(override_target)
    print(f"Target: {host}:{port}\n")

    steps = scenario.get("steps") or []
    if not steps:
        print("Escenario sin steps.", file=sys.stderr)
        return 1

    ok = 0
    for i, step in enumerate(steps, 1):
        account = str(step.get("account", ""))
        code = str(step.get("code", ""))
        if not account or not code:
            print(f"Step {i}: account/code requeridos, saltando.", file=sys.stderr)
            continue
        qualifier = step.get("qualifier", "E")
        zone = str(step.get("zone", "001"))
        partition = str(step.get("partition", "01"))
        note = step.get("note", "")
        prefix = f"[{i}/{len(steps)}]"
        if note:
            print(f"{prefix} {note}")
        else:
            print(f"{prefix}")
        success = send_signal(host, port, account, code, qualifier, partition, zone)
        if success:
            ok += 1
        delay = step.get("delay_after", 0)
        if delay and i < len(steps):
            time.sleep(delay)

    print(f"\nResumen: {ok}/{len(steps)} señales enviadas.")
    return 0 if ok == len(steps) else 1


def main():
    parser = argparse.ArgumentParser(description="Runner de escenarios YAML para el emulador")
    parser.add_argument("scenario", type=Path, help="Ruta al archivo YAML")
    parser.add_argument("--target", help="host[:port] que sobrescribe el del YAML")
    args = parser.parse_args()
    if not args.scenario.exists():
        print(f"Escenario no existe: {args.scenario}", file=sys.stderr)
        return 1
    return run_scenario(args.scenario, args.target)


if __name__ == "__main__":
    sys.exit(main())
