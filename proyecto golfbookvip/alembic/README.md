# Migraciones (Alembic) — GolfBookVIP

## Estado
- **`0001_baseline`** — reproduce el esquema de producción 1:1 (43 tablas). Ejecuta el DDL de
  `alembic/baseline_schema.sql` (dump `--schema-only` de la BD viva). Verificado end-to-end en Docker:
  BD vacía → `alembic upgrade head` → esquema idéntico a prod (diff de tablas vacío; único delta = la
  tabla `alembic_version`).
- **`0002_seed_plans`** — siembra los 6 planes (`free_player`, `player_pro`, `free_club`, `club_starter`,
  `club_pro`, `club_enterprise`). Idempotente (`ON CONFLICT (code) DO NOTHING`).

## Disciplina anti-drift (obligatoria desde ahora)
Todo cambio de esquema = una migración Alembic generada desde los modelos:
```
alembic revision --autogenerate -m "descripcion"
```
`Base.metadata` está alineado con prod: un autogenerate contra una BD en `head` debe salir **vacío**,
salvo el quirk documentado abajo. Cualquier otra operación en el autogenerate = un cambio real que revisar.

## Quirk conocido (ignorar)
Un autogenerate contra una BD en head emite SIEMPRE un drop+create de las 2 FKs de `player_hole_stats`
(`player_hole_stats_user_id_fkey`, `player_hole_stats_course_id_fkey`) con **nombre, columnas y
`ON DELETE CASCADE` idénticos**. Es un artefacto de cualificación de esquema de Alembic
(`source_schema='public'` en un lado y no en el otro) combinado con el ciclo de FKs
`clubs ↔ membership_types`; el DDL neto es NULO. **No es drift.** Al generar una migración real, borra a
mano esas 4 líneas de `player_hole_stats` del archivo generado si aparecen solas.

## Adoptar Alembic en la prod existente
Ver `_baseline_source/CUTOVER_PROD.md` — se hace `alembic stamp 0001_baseline` (marca el baseline como
aplicado sin re-ejecutar DDL, porque las tablas ya existen) y de ahí en adelante `alembic upgrade head`.

## Levantar staging reproducible desde cero
```
docker compose -p gbv_staging -f docker-compose.staging.yml up -d --build
# api en http://localhost:8110/health  · Postgres NO expuesto · volúmenes limpios
```
