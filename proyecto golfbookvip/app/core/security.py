from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import hmac, hashlib, base64, time as _time
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings

_RESET_EXPIRY = 3600  # 1 hour

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "access"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": subject, "exp": expire, "type": "refresh"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def create_reset_token(user_id: str, password_hash: str) -> str:
    """HMAC-signed reset token valid for 1 hour. Invalidated automatically when password changes."""
    ts = int(_time.time())
    key = settings.SECRET_KEY.encode()
    msg = f"{user_id}:{ts}:{password_hash[:12]}".encode()
    sig = hmac.new(key, msg, digestmod=hashlib.sha256).hexdigest()[:16]
    raw = f"{ts}:{user_id}:{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def verify_reset_token(token: str, password_hash: str) -> Optional[str]:
    """Returns user_id if token is valid and not expired, None otherwise."""
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        ts_str, user_id, sig = raw.split(":", 2)
        if _time.time() - int(ts_str) > _RESET_EXPIRY:
            return None
        key = settings.SECRET_KEY.encode()
        msg = f"{user_id}:{int(ts_str)}:{password_hash[:12]}".encode()
        expected = hmac.new(key, msg, digestmod=hashlib.sha256).hexdigest()[:16]
        if not hmac.compare_digest(sig, expected):
            return None
        return user_id
    except Exception:
        return None
