"""Estado por conversación (SQLite) — historial para el LLM + flag de orden creada.

Necesario porque el token del AgentBot NO puede leer la conversación ni escribir
atributos en Chatwoot, así que el bot mantiene su propio contexto. Se persiste en un
volumen docker para sobrevivir reinicios.
"""

import sqlite3
import threading
import time

import config

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def _db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(config.STATE_DB_PATH, check_same_thread=False)
        _conn.execute("""CREATE TABLE IF NOT EXISTS messages (
            conv_id INTEGER, role TEXT, content TEXT, ts REAL)""")
        _conn.execute("""CREATE TABLE IF NOT EXISTS conv_state (
            conv_id INTEGER PRIMARY KEY, order_folio TEXT, ts REAL)""")
        _conn.execute("""CREATE TABLE IF NOT EXISTS pending_photos (
            conv_id INTEGER, url TEXT, ts REAL)""")
        _conn.commit()
    return _conn


def add_message(conv_id: int, role: str, content: str):
    """Guarda un turno (role='user'|'assistant')."""
    with _lock:
        db = _db()
        db.execute("INSERT INTO messages(conv_id,role,content,ts) VALUES (?,?,?,?)",
                   (conv_id, role, content, time.time()))
        db.commit()


def get_history(conv_id: int, limit: int) -> list[dict]:
    """Últimos `limit` turnos en formato OpenAI [{role, content}, ...] (cronológico)."""
    with _lock:
        rows = _db().execute(
            "SELECT role,content FROM messages WHERE conv_id=? ORDER BY rowid DESC LIMIT ?",
            (conv_id, limit)).fetchall()
    return [{"role": r, "content": c} for r, c in reversed(rows)]


def get_order(conv_id: int) -> str | None:
    with _lock:
        row = _db().execute("SELECT order_folio FROM conv_state WHERE conv_id=?",
                            (conv_id,)).fetchone()
    return row[0] if row else None


def set_order(conv_id: int, folio: str):
    with _lock:
        db = _db()
        db.execute("INSERT OR REPLACE INTO conv_state(conv_id,order_folio,ts) VALUES (?,?,?)",
                   (conv_id, folio, time.time()))
        db.commit()


# ── Fotos pendientes de adjuntar a la orden ──

def add_photo(conv_id: int, url: str):
    with _lock:
        db = _db()
        db.execute("INSERT INTO pending_photos(conv_id,url,ts) VALUES (?,?,?)",
                   (conv_id, url, time.time()))
        db.commit()


def get_photos(conv_id: int) -> list[str]:
    with _lock:
        rows = _db().execute("SELECT url FROM pending_photos WHERE conv_id=?",
                            (conv_id,)).fetchall()
    return [r[0] for r in rows]


def clear_photos(conv_id: int):
    with _lock:
        db = _db()
        db.execute("DELETE FROM pending_photos WHERE conv_id=?", (conv_id,))
        db.commit()
