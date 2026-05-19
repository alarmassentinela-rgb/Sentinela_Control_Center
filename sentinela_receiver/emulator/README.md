# Emulador Sentinela

Simula paneles de alarma DT42/Surgard Contact ID contra el receiver Sentinela.

## Instalación

```bash
pip install pyyaml
```

## dt42_emulator.py — uno-a-uno

Interactivo (menú):
```bash
python3 dt42_emulator.py
```

One-shot por CLI:
```bash
# Robo desde la cuenta 1025 al receiver LAB
python3 dt42_emulator.py --target 192.168.3.2:10002 \
    --account 1025 --code 130 --zone 003

# Restauración (qualifier R)
python3 dt42_emulator.py --account 1025 --code 401 --qualifier R --zone 005

# Cuenta inexistente — debe entrar a cuarentena (v18.0.1.3.7+)
python3 dt42_emulator.py --target 192.168.3.2:10002 \
    --account 4242 --code 130
```

Modo automático (varias señales seguidas):
```bash
python3 dt42_emulator.py --account 1025 --code 130 --auto --count 5 --interval 2
```

## scenario_runner.py — escenarios YAML

```bash
python3 scenario_runner.py scenarios/basic_signals.yaml
python3 scenario_runner.py scenarios/heartbeat_storm.yaml --target 192.168.3.2:10002
python3 scenario_runner.py scenarios/panel_offline.yaml
```

`--target` sobrescribe el host:port del YAML — útil para apuntar LAB (10002)
vs PROD (10001) sin tocar el archivo.

## Escenarios incluidos

| Archivo | Qué valida |
|---|---|
| `basic_signals.yaml` | 9 señales Contact ID comunes desde cuenta 1025 |
| `heartbeat_storm.yaml` | Ráfaga de 20 señales (200ms cada una) — verifica que receiver no pierde |
| `panel_offline.yaml` | Flujo de auto-cierre del trouble `[AUTO_OFFLINE]` cuando panel vuelve a reportar (requiere setup previo en DB) |
