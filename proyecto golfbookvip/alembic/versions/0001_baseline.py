"""baseline schema from live production dump

Revision ID: 0001_baseline
Revises:
Create Date: 2026-07-01
"""

from pathlib import Path

from alembic import op


revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


REQUIRED_EXTENSIONS_SQL = """
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS "pg_trgm" WITH SCHEMA public;
CREATE EXTENSION IF NOT EXISTS "unaccent" WITH SCHEMA public;
"""


def _baseline_dump_path() -> Path:
    return Path(__file__).resolve().parents[1] / "baseline_schema.sql"


def _clean_dump_sql() -> str:
    lines: list[str] = []
    for raw_line in _baseline_dump_path().read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("--") or stripped.startswith("\\"):
            continue
        if stripped.startswith("SET "):
            continue
        if stripped.startswith("SELECT pg_catalog.set_config"):
            continue
        if stripped.startswith("COMMENT ON EXTENSION"):
            continue
        if stripped.startswith("CREATE EXTENSION"):
            continue
        lines.append(raw_line)
    return REQUIRED_EXTENSIONS_SQL + "\n" + "\n".join(lines)


def _split_sql_statements(sql: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_single_quote = False
    i = 0
    while i < len(sql):
        char = sql[i]
        current.append(char)
        if char == "'":
            if i + 1 < len(sql) and sql[i + 1] == "'":
                current.append(sql[i + 1])
                i += 1
            else:
                in_single_quote = not in_single_quote
        elif char == ";" and not in_single_quote:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        i += 1
    trailing = "".join(current).strip()
    if trailing:
        statements.append(trailing)
    return statements


def upgrade() -> None:
    bind = op.get_bind()
    for statement in _split_sql_statements(_clean_dump_sql()):
        bind.exec_driver_sql(statement)


def downgrade() -> None:
    # Baseline adoption is one-way for production safety; do not drop live data.
    pass
