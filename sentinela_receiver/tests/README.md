# Tests end-to-end del receiver Sentinela

Tests pytest que ejercitan el flujo completo: emulador TCP → receiver → Odoo
XML-RPC → DB. Por defecto apuntan a la instancia LAB (`Sentinela_STAGING`,
puerto 10002).

## Requisitos

- `pytest` y `PyYAML` (`pip install pytest pyyaml`)
- Receiver LAB corriendo (verificar con `ss -tlnp | grep 10002` en server)
- Cuenta de prueba `1025` (device id 4) creada en STAGING

## Ejecución

```bash
export SENTINELA_TEST_PASSWORD='__SET_ME__'
cd sentinela_receiver/tests
pytest -v
```

Sin `SENTINELA_TEST_PASSWORD` los tests se saltan (skip).

## Variables de entorno

| Variable | Default | Notas |
|---|---|---|
| `SENTINELA_TEST_PASSWORD` | (sin default) | requerido — auth XML-RPC |
| `SENTINELA_TEST_URL` | `http://192.168.3.2:8070` | endpoint Odoo |
| `SENTINELA_TEST_DB` | `Sentinela_STAGING` | NUNCA apuntar a `Sentinela_V18` |
| `SENTINELA_TEST_USER` | `api_user` | usuario XML-RPC |
| `SENTINELA_TEST_RECEIVER` | `192.168.3.2:10002` | host:port del receiver |
| `SENTINELA_TEST_ACCOUNT` | `1025` | cuenta conocida |
| `SENTINELA_TEST_DEVICE_ID` | `4` | id del device de la cuenta |

## Qué se valida

| Archivo | Casos |
|---|---|
| `test_normal_flow.py` | Señal de cuenta conocida crea signal + event y actualiza last_communication |
| `test_quarantine.py` | Cuenta desconocida → signal con is_quarantine=True, sin device ni event |
| `test_offline_detection.py` | Cron `_cron_detect_offline_panels` crea trouble [AUTO_OFFLINE], es idempotente, y la señal de panel cierra el evento |

## Limpieza

- Las señales de cuarentena se borran al final de cada test
- El device de prueba se resetea (`expected_heartbeat_hours=0`, status=active)
  y los eventos `[AUTO_OFFLINE]` abiertos se cierran
- Las señales normales (no-cuarentena) NO se borran — quedan en STAGING como
  histórico. Si esto se vuelve molesto, ampliar el cleanup.

## Seguridad

Los tests NUNCA deben correr contra `Sentinela_V18`. La protección hoy es por
default de variables de entorno; no hay assertion explícito. Si quieres usar
otra DB de pruebas, sobrescribe `SENTINELA_TEST_DB` deliberadamente.
