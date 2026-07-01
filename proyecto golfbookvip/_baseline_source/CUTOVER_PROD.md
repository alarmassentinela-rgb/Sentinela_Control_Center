# Cutover de producción a Alembic

Este procedimiento adopta Alembic sobre la base viva existente sin recrear tablas ni datos.

## Precondiciones

- Confirmar que el esquema vivo de producción coincide con `alembic/baseline_schema.sql`.
- Confirmar que `alembic_version` no existe todavía en producción.
- Tener backup reciente y verificado antes de tocar la base viva.

## Procedimiento

1. Desplegar el código que contiene `0001_baseline` y `0002_seed_plans`.
2. Marcar el baseline como ya aplicado, sin ejecutar DDL:

```bash
docker exec golfbookvip_api alembic stamp 0001_baseline
```

Alternativa si se usa un contenedor efímero de migración conectado a la misma red y variables de producción:

```bash
docker compose run --rm migrate alembic stamp 0001_baseline
```

3. Verificar que Alembic creó la tabla de control:

```bash
docker exec golfbookvip_db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT * FROM alembic_version;"
```

El valor esperado después del stamp es:

```text
0001_baseline
```

4. Aplicar migraciones posteriores al baseline:

```bash
docker exec golfbookvip_api alembic upgrade head
```

En esta fase, `0002_seed_plans` es idempotente y usa `ON CONFLICT (code) DO NOTHING`.

## Rollback operativo

No ejecutar `alembic downgrade` para el baseline en producción. `0001_baseline` representa el esquema que ya
existe y su `downgrade()` es intencionalmente no destructivo para proteger datos.
