# -*- coding: utf-8 -*-
"""Contraseñas con Argon2 + política. (W5.8)"""
from passlib.context import CryptContext

from ..config import settings

_ctx = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return _ctx.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ctx.verify(password or "", password_hash or "")
    except Exception:
        return False


def validate_policy(password: str):
    """Devuelve (ok, motivo). Política: longitud mínima, letras+dígitos, no repetitiva."""
    if not password or len(password) < settings.password_min_length:
        return False, "too_short"
    if password.isdigit() or password.isalpha():
        return False, "needs_letters_and_digits"
    if len(set(password)) < 3:
        return False, "too_repetitive"
    return True, None
