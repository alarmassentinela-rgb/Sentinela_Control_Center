# Sentinela Alarm Receiver

Unified TCP receiver for the `sentinela_monitoring` module. Replaces the legacy `receiver_v6.py` family.

## Layout

```
sentinela_receiver/
├── receiver.py                  # entry point
├── parsers/                     # protocol parsers (Contact ID today, SIA/MLR2 future)
├── config_prod.yaml.example     # production template (real config gitignored)
├── config_lab.yaml.example      # lab template
├── systemd/                     # service units for both instances
├── emulator/                    # panel emulator + YAML scenarios for testing
├── _legacy/                     # archived old receiver versions
└── logs/                        # runtime log files (gitignored)
```

## Configuración inicial

Copia los `*.example` y rellena `odoo_password`:

```bash
cp config_lab.yaml.example config_lab.yaml
cp config_prod.yaml.example config_prod.yaml
$EDITOR config_lab.yaml config_prod.yaml
```

Los archivos `config_lab.yaml` y `config_prod.yaml` están gitignored — nunca subir credenciales en claro.

## Run

```bash
python3 receiver.py config_lab.yaml
python3 receiver.py config_prod.yaml
```

## Install as systemd services

```bash
sudo cp systemd/sentinela-receiver-lab.service /etc/systemd/system/
sudo cp systemd/sentinela-receiver-prod.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now sentinela-receiver-lab.service
sudo systemctl enable --now sentinela-receiver-prod.service
```

## Architecture

- One process per Odoo DB. Two instances run side-by-side (prod 10001, lab 10002).
- Heartbeat thread independent of incoming signals — keeps the dashboard "online" even when the panel is quiet.
- Every TCP connection's raw bytes go to `sentinela.alarm.signal.raw_data` (hex), parsed or not.
- Parser is pluggable via `config.parser`. Today only `contact_id`.
- Firewall on the server limits ports 10001/10002 to LAN (192.168.3.0/24).

## Adding a parser

Drop a class in `parsers/` with a `parse(data: bytes) -> dict | None` method, register it in `parsers/__init__.PARSERS`.
