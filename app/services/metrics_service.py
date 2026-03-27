# app/services/metrics_service.py
import time
import threading
from collections import defaultdict
from typing import Dict, Optional
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

class MetricsService:
    def __init__(self):
        self._counters: Dict[str, int] = defaultdict(int)
        self._latencies: Dict[str, list] = defaultdict(list)
        self._errors: Dict[str, int] = defaultdict(int)
        self._lock = threading.Lock()

        # Prometheus metrics
        self.chat_requests = Counter("chat_requests_total", "Total chat requests")
        self.chat_errors = Counter("chat_errors_total", "Total chat errors")
        self.chat_latency = Histogram("chat_latency_seconds", "Chat request latency")
        self.agent_duration = Histogram("agent_duration_seconds", "Agent duration by name")

    def increment(self, metric: str, value: int = 1):
        with self._lock:
            self._counters[metric] += value

    def increment_errors(self, metric: str, value: int = 1):
        with self._lock:
            self._errors[metric] += value

    def record_latency(self, metric: str, latency_ms: float):
        with self._lock:
            self._latencies[metric].append(latency_ms)
        if metric == "chat":
            self.chat_latency.observe(latency_ms / 1000)

    def get(self, metric: str) -> int:
        return self._counters.get(metric, 0)

    def get_error_rate(self, metric: str) -> float:
        total = self._counters.get(f"{metric}_requests_total", 0)
        errors = self._errors.get(f"{metric}_errors_total", 0)
        return errors / total if total > 0 else 0.0

    def get_latency_p50(self, metric: str) -> float:
        lats = sorted(self._latencies.get(metric, []))
        if not lats:
            return 0.0
        idx = int(len(lats) * 0.5)
        return lats[min(idx, len(lats) - 1)]

    def get_latency_p99(self, metric: str) -> float:
        lats = sorted(self._latencies.get(metric, []))
        if not lats:
            return 0.0
        idx = int(len(lats) * 0.99)
        return lats[min(idx, len(lats) - 1)]

    def record_agent_duration(self, agent_name: str, duration_ms: float):
        self.agent_duration.labels(agent=agent_name).observe(duration_ms / 1000)

    def get_summary(self) -> dict:
        return {
            "qps": self._counters.get("chat_requests_total", 0),
            "latency_p50_ms": self.get_latency_p50("chat"),
            "latency_p99_ms": self.get_latency_p99("chat"),
            "error_rate": self.get_error_rate("chat"),
        }

    def _reset(self):
        self._counters.clear()
        self._latencies.clear()
        self._errors.clear()

_svc: Optional[MetricsService] = None

def get_metrics_service() -> MetricsService:
    global _svc
    if _svc is None:
        _svc = MetricsService()
    return _svc