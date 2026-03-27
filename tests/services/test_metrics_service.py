from app.services.metrics_service import MetricsService, get_metrics_service
import time

def test_increment_and_get_qps():
    svc = get_metrics_service()
    svc._reset()
    for _ in range(10):
        svc.increment("chat_requests_total")
    assert svc.get("chat_requests_total") == 10

def test_record_latency():
    svc = get_metrics_service()
    svc._reset()
    svc.record_latency("chat", 1500)
    svc.record_latency("chat", 2500)
    assert svc.get_latency_p50("chat") >= 1500
    assert svc.get_latency_p99("chat") >= 2500

def test_error_rate():
    svc = get_metrics_service()
    svc._reset()
    svc.increment("chat_requests_total")
    svc.increment("chat_requests_total")
    svc.increment_errors("chat_errors_total")
    rate = svc.get_error_rate("chat")
    assert rate == 0.5