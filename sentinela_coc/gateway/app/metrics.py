# -*- coding: utf-8 -*-
"""Métricas en memoria (disponibilidad y tiempos de respuesta del proveedor).

Sin dependencias externas. Expuestas en /metrics (texto Prometheus) y /v1/providers/health.
NUNCA registra secretos ni OTP.
"""
import threading


class Metrics:
    def __init__(self):
        self._lock = threading.Lock()
        self.counters: dict[str, int] = {}
        self.gauges: dict[str, float] = {}
        self.latency = {"count": 0, "sum_ms": 0.0, "last_ms": 0.0}

    def inc(self, name, **labels):
        key = name + "".join(f"|{k}={v}" for k, v in sorted(labels.items()))
        with self._lock:
            self.counters[key] = self.counters.get(key, 0) + 1

    def set_gauge(self, name, value):
        with self._lock:
            self.gauges[name] = float(value)

    def observe_latency(self, ms):
        with self._lock:
            self.latency["count"] += 1
            self.latency["sum_ms"] += ms
            self.latency["last_ms"] = ms

    def snapshot(self):
        with self._lock:
            count = self.latency["count"]
            avg = (self.latency["sum_ms"] / count) if count else 0.0
            return {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "latency": {**self.latency, "avg_ms": avg},
            }

    def prometheus(self) -> str:
        snap = self.snapshot()
        lines = []
        for k, v in snap["counters"].items():
            parts = k.split("|")
            name = parts[0]
            labels = parts[1:]
            lab = ("{" + ",".join(p.replace("=", '="') + '"' for p in labels) + "}") if labels else ""
            lines.append(f"{name}{lab} {v}")
        for k, v in snap["gauges"].items():
            lines.append(f"{k} {v}")
        lat = snap["latency"]
        lines.append(f"otp_send_latency_ms_last {lat['last_ms']:.1f}")
        lines.append(f"otp_send_latency_ms_avg {lat['avg_ms']:.1f}")
        lines.append(f"otp_send_latency_count {lat['count']}")
        return "\n".join(lines) + "\n"


metrics = Metrics()
