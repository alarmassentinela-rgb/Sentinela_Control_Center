# -*- coding: utf-8 -*-
"""Hashing/generación de secretos. El OTP se guarda SOLO como hash (con pepper)."""
import hashlib
import hmac
import secrets


def hash_secret(value: str, pepper: str) -> str:
    """HMAC-SHA256 con pepper del servidor. Para OTP y refresh tokens."""
    return hmac.new(pepper.encode(), (value or "").encode(), hashlib.sha256).hexdigest()


def constant_eq(a: str, b: str) -> bool:
    return hmac.compare_digest(a or "", b or "")


def gen_otp(length: int = 6) -> str:
    return f"{secrets.randbelow(10 ** length):0{length}d}"


def gen_token() -> str:
    return secrets.token_urlsafe(32)
