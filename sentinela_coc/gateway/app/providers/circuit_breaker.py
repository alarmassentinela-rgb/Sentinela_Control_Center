# -*- coding: utf-8 -*-
"""Circuit Breaker simple (closed → open → half-open). `clock` inyectable para pruebas."""
import time


class CircuitBreaker:
    def __init__(self, fail_threshold=5, cooldown_sec=30, clock=time.monotonic):
        self.fail_threshold = fail_threshold
        self.cooldown = cooldown_sec
        self.clock = clock
        self.failures = 0
        self.opened_at = None
        self.state = "closed"

    def allow(self) -> bool:
        if self.state == "open":
            if self.opened_at is not None and (self.clock() - self.opened_at) >= self.cooldown:
                self.state = "half_open"
                return True
            return False
        return True

    def record_success(self):
        self.failures = 0
        self.opened_at = None
        self.state = "closed"

    def record_failure(self):
        self.failures += 1
        if self.state == "half_open" or self.failures >= self.fail_threshold:
            self.state = "open"
            self.opened_at = self.clock()
