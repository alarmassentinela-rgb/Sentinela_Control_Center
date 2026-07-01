# FASE 1 — Cimientos reproducibles (staging desde cero)

> Contrato de trabajo para Codex. El Arquitecto (Claude) revisará el resultado línea por línea
> contra esta especificación. NO toques producción. Todo se prueba en un stack Docker
> desechable y aislado.

## Contexto y verdad de campo

- Proyecto: `proyecto golfbookvip` (FastAPI + SQLAlchemy 2.0 async + Alembic + Postgres 16).
- **Problema raíz:** el esquema NO es reproducible. `postgres/init.sql` solo crea extensiones (0 tablas),
  `alembic/versions/` está VACÍO, la app no hace `create_all`, y `golfbookvip_schema.sql` está huérfano y
  obsoleto (v1.0). En prod **no existe la tabla `alembic_version`** (Alembic nunca corrió).
- **Verdad de campo (autoritativa), ya volcada del Postgres VIVO de producción:**
  - `_baseline_source/prod_schema_live.sql` — `pg_dump --schema-only` de la BD real (43 tablas). ESTE es el
    esquema objetivo. El baseline debe reproducirlo EXACTAMENTE.
  - `_baseline_source/seed_plans.sql` — datos actuales de `subscription_plans` + `plan_features`
    (los 6 planes free/pro/club). Semilla obligatoria para un entorno nuevo.
- **Drift a nivel de tabla:** los modelos SQLAlchemy cubren 42 de 43 tablas. La única tabla en prod SIN modelo
  es `round_teams`:
  ```sql
  CREATE TABLE public.round_teams (
      id uuid DEFAULT gen_random_uuid() NOT NULL,
      round_id uuid NOT NULL,
      team_number integer NOT NULL,
      name character varying(50) NOT NULL,
      color character varying(20) NOT NULL,
      created_at timestamp with time zone DEFAULT now()
  );
  ```

## Objetivo de la fase

Que `docker compose up` sobre volúmenes limpios levante un entorno **idéntico a producción** de forma
reproducible, y que exista una vía de migración hacia adelante. Esto también nos da el STAGING para probar
las siguientes fases sin riesgo.

## Entregables (en este orden)

### 1. Modelo faltante `RoundTeam`
- Crea el modelo `RoundTeam` en `app/models/round.py` que mapee EXACTAMENTE la tabla `round_teams` de arriba
  (tipos, nullability y defaults idénticos: `id` uuid pk con `gen_random_uuid()`, FK `round_id`→`rounds.id`,
  `team_number` int not null, `name` varchar(50) not null, `color` varchar(20) not null, `created_at` timestamptz default now()).
- Regístralo en `app/models/__init__.py` (import + `__all__`).
- NO cambies otras tablas.

### 2. Migración baseline de Alembic (0001)
- Configura Alembic para async correctamente: `alembic/env.py` debe importar `Base.metadata` desde
  `app.models` (target_metadata), leer `DATABASE_URL` desde `app.core.config.settings`, y funcionar con el
  driver `postgresql+asyncpg` (usa `run_sync` / `connectable` async como en el patrón oficial de Alembic async).
- Crea la migración **`0001_baseline`** cuyo `upgrade()` reproduzca el esquema de `prod_schema_live.sql`
  EXACTAMENTE (todas las 43 tablas, PKs, FKs, unique constraints, índices, defaults y extensiones necesarias:
  `uuid-ossp`, `pg_trgm`, `unaccent`; `postgis` NO es necesaria salvo que el dump la use en alguna columna —
  verifícalo en el dump y solo créala si se usa). `downgrade()` puede hacer `drop` de todo o quedar como no-op
  documentado.
  - Método permitido y preferido por su fidelidad: que `upgrade()` ejecute el DDL del dump (puedes incrustar el
    SQL del dump, limpiándolo de las líneas de `pg_dump` no portables — `\restrict`, `SET`, comentarios de
    ownership — y dejando solo `CREATE EXTENSION` / `CREATE TABLE` / `ALTER TABLE ADD CONSTRAINT` / `CREATE INDEX`).
    El objetivo es fidelidad 1:1 con prod, no elegancia.
- **Criterio de aceptación del baseline:** partir de una BD vacía y correr `alembic upgrade head` debe producir
  un esquema cuyo `pg_dump --schema-only` sea equivalente al de prod (mismas tablas, columnas, constraints e
  índices). Diferencias solo cosméticas (orden, nombres autogenerados de constraints) son aceptables si son
  funcionalmente equivalentes; documenta cualquiera.

### 3. Migración de semilla (0002_seed_plans)
- Migración de datos que inserte los 6 planes de `_baseline_source/seed_plans.sql` (idempotente:
  `INSERT ... ON CONFLICT (code) DO NOTHING` o equivalente). Un entorno nuevo debe tener los planes.

### 4. Verificación de que los MODELOS concuerdan con el baseline (anti-drift a futuro)
- Tras aplicar 0001, corre `alembic revision --autogenerate` en seco y AJUSTA los modelos (no el baseline)
  hasta que el autogenerate produzca un diff **vacío** (o solo diferencias cosméticas justificadas y
  documentadas). Esto garantiza que `Base.metadata` == esquema real. Entrega un breve reporte de qué columnas
  ajustaste en los modelos.
- Objetivo: de aquí en adelante, todo cambio de esquema = una migración Alembic generada desde los modelos.

### 5. Stack de staging reproducible desde cero
- Añade `docker-compose.staging.yml` (project name distinto, p.ej. `gbv_staging`, puertos que NO colisionen con
  prod: api en 8110, db interna, sin exponer Postgres al host, sin Portainer) que use **volúmenes limpios**.
- El servicio `migrate` debe correr `alembic upgrade head` y el `api` arrancar solo tras `migrate` exitoso.
- Corrige `postgres/init.sql`: que SOLO tenga extensiones (ya está bien); las tablas las crea Alembic, no init.sql.
- **Prueba end-to-end tú mismo** con un nombre de proyecto aislado y volúmenes efímeros:
  `docker compose -p gbv_staging_test -f docker-compose.staging.yml up -d` → esperar healthy →
  `curl :8110/health` == `{"status":"ok"}` → verificar que las 43 tablas + `alembic_version` existen →
  `docker compose -p gbv_staging_test ... down -v`. Reporta la salida real.
- Si NO tienes Docker disponible en tu entorno, NO inventes la verificación: entrega los archivos y di
  explícitamente "no pude ejecutar Docker; pendiente de verificación por el Arquitecto".

### 6. Higiene de dependencias (bajo riesgo, mejora reproducibilidad)
- En `requirements.txt`: ELIMINA `uuid==1.30` (backport roto que ensombrece la stdlib en Py3), ELIMINA
  `aioredis==2.0.1` (deprecado y en conflicto con `redis`), y quita el `httpx` DUPLICADO (déjalo una vez).
- Verifica que nada en `app/` importe `uuid` el paquete-backport ni `aioredis` (usa la stdlib `uuid` y, si
  acaso, `redis.asyncio`). NO agregues Redis al código en esta fase (eso es fase posterior).

### 7. Documentación del cutover de prod (NO ejecutarlo)
- Escribe `_baseline_source/CUTOVER_PROD.md` con el procedimiento para adoptar Alembic en la prod existente SIN
  recrear datos: correr `alembic stamp 0001_baseline` en la BD viva (marca el baseline como aplicado sin correr
  DDL, porque las tablas ya existen), verificar que aparece `alembic_version`, y de ahí en adelante
  `alembic upgrade head` para futuras migraciones. Incluir el comando exacto vía
  `docker exec golfbookvip_db` / contenedor migrate. Este archivo es guía; el Arquitecto lo ejecutará.

## Reglas
- NO toques `rounds.py`, `clubs.py`, la lógica de negocio, ni el frontend en esta fase. Solo: modelos (mínimo
  para round_teams + alineación), alembic/, docker-compose.staging.yml, postgres/init.sql, requirements.txt,
  y los .md de `_baseline_source/`.
- NO te conectes a producción (192.168.3.2). Trabaja solo con la verdad de campo ya volcada en
  `_baseline_source/`.
- Dinero, seguridad y multitenencia son fases siguientes; no las abordes aquí.
- Entrega un resumen final: archivos creados/modificados, resultado de la prueba Docker (o por qué no pudiste),
  y el reporte de ajustes de modelos del paso 4.
