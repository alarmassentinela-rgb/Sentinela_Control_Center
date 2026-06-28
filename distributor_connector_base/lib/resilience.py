"""Resiliencia de red para conectores: rate limiting, backoff exponencial,
circuit breaker y timeouts. Sin dependencias de Odoo; clock/sleep inyectables
para pruebas deterministas.
"""
from __future__ import annotations

import threading
import time
from typing import Callable, List

from .exceptions import CircuitOpenError


# --------------------------------------------------------------------------
# Backoff exponencial con jitter
# --------------------------------------------------------------------------
def backoff_delays(retries: int, base: float = 0.5, cap: float = 30.0,
                   jitter: bool = True, rand: Callable[[], float] = None) -> List[float]:
    """Lista de esperas (s) para `retries` reintentos: base*2**n acotado a cap (+jitter)."""
    rand = rand or __import__("random").random
    out = []
    for n in range(max(0, retries)):
        delay = min(cap, base * (2 ** n))
        if jitter:
            delay = delay * (0.5 + 0.5 * rand())  # 50%-100% del valor
        out.append(round(delay, 4))
    return out


# --------------------------------------------------------------------------
# Token-bucket rate limiter (thread-safe)
# --------------------------------------------------------------------------
class RateLimiter:
    """Limita a `rate_per_min` operaciones/min. `acquire()` espera si hace falta."""

    def __init__(self, rate_per_min: int,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        self.capacity = max(1, int(rate_per_min))
        self.tokens = float(self.capacity)
        self.refill_per_sec = self.capacity / 60.0
        self._clock = clock
        self._sleep = sleep
        self._last = clock()
        self._lock = threading.Lock()

    def _refill(self):
        now = self._clock()
        elapsed = now - self._last
        if elapsed > 0:
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_sec)
            self._last = now

    def acquire(self, n: int = 1) -> float:
        """Toma n tokens; devuelve los segundos que tuvo que esperar."""
        waited = 0.0
        with self._lock:
            while True:
                self._refill()
                if self.tokens >= n:
                    self.tokens -= n
                    return waited
                need = (n - self.tokens) / self.refill_per_sec
                self._sleep(need)
                waited += need


# --------------------------------------------------------------------------
# Circuit breaker
# --------------------------------------------------------------------------
class CircuitBreaker:
    """CLOSED → (fallos≥umbral) → OPEN → (tras recovery) → HALF_OPEN → CLOSED/OPEN."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0,
                 clock: Callable[[], float] = time.monotonic):
        self.failure_threshold = max(1, int(failure_threshold))
        self.recovery_timeout = float(recovery_timeout)
        self._clock = clock
        self._failures = 0
        self._state = self.CLOSED
        self._opened_at = 0.0
        self._lock = threading.Lock()

    @property
    def state(self) -> str:
        with self._lock:
            if self._state == self.OPEN and (self._clock() - self._opened_at) >= self.recovery_timeout:
                self._state = self.HALF_OPEN
            return self._state

    def record_success(self):
        with self._lock:
            self._failures = 0
            self._state = self.CLOSED

    def record_failure(self):
        with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = self.OPEN
                self._opened_at = self._clock()

    def call(self, fn: Callable, *args, **kwargs):
        """Ejecuta fn con protección. Lanza CircuitOpenError si está abierto."""
        if self.state == self.OPEN:
            raise CircuitOpenError("Circuit breaker abierto")
        try:
            result = fn(*args, **kwargs)
        except Exception:
            self.record_failure()
            raise
        self.record_success()
        return result
