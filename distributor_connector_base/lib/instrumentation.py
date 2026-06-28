"""Instrumentación de performance: mide duración de operaciones (llamada API,
normalización, caché, promoción, sincronización) para alimentar catalog.metric.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Callable, Optional

# Nombres de métrica estándar
M_API_CALL = "api_call"
M_NORMALIZE = "normalize"
M_CACHE = "cache"
M_PROMOTION = "promotion"
M_SYNC = "sync"


class Timer:
    def __init__(self, clock: Callable[[], float] = time.perf_counter):
        self._clock = clock
        self.ms = 0.0

    def __enter__(self):
        self._t0 = self._clock()
        return self

    def __exit__(self, *exc):
        self.ms = round((self._clock() - self._t0) * 1000.0, 3)
        return False


@contextmanager
def measure(sink: Optional[Callable[[float], None]] = None,
            clock: Callable[[], float] = time.perf_counter):
    """`with measure(sink) as t:` → al salir, t.ms tiene los ms y se llama sink(ms)."""
    t = Timer(clock)
    t.__enter__()
    try:
        yield t
    finally:
        t.__exit__()
        if sink:
            sink(t.ms)
