"""Versionado del Catalog Engine (independiente de la versión Odoo del manifest).

SemVer: major rompe contrato, minor agrega, patch corrige. Cada conector declara
`requires_engine` (ej. ">=1.0,<2.0") y se valida al registrarse.
"""
from __future__ import annotations

ENGINE_VERSION = "1.0.0"


def parse(v: str) -> tuple:
    """'1.2.3' -> (1, 2, 3). Tolera 'v1.2' y sufijos."""
    nums = []
    for part in str(v).lstrip("vV").split(".")[:3]:
        digits = "".join(ch for ch in part if ch.isdigit())
        nums.append(int(digits) if digits else 0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums)


def _check_one(version: tuple, op: str, target: tuple) -> bool:
    if op == ">=":
        return version >= target
    if op == ">":
        return version > target
    if op == "<=":
        return version <= target
    if op == "<":
        return version < target
    if op in ("==", "="):
        return version == target
    raise ValueError("Operador de versión no soportado: %r" % op)


def is_compatible(engine_version: str, requires: str) -> bool:
    """Valida un spec tipo '>=1.0,<2.0' (AND separado por coma) contra la versión del motor."""
    if not requires:
        return True
    ev = parse(engine_version)
    for clause in requires.split(","):
        clause = clause.strip()
        if not clause:
            continue
        for op in (">=", "<=", "==", "=", ">", "<"):
            if clause.startswith(op):
                if not _check_one(ev, op, parse(clause[len(op):].strip())):
                    return False
                break
        else:
            raise ValueError("Cláusula de versión inválida: %r" % clause)
    return True
