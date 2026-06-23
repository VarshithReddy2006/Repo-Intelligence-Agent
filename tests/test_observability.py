import pytest
from fastapi import FastAPI, Response
from fastapi.testclient import TestClient
from backend.logging_middleware import RequestIdMiddleware
from backend.security_middleware import RateLimitMiddleware
from backend.metrics_middleware import MetricsMiddleware
from backend.logging_config import configure_logging, request_id_var
from core.metrics import metrics_registry


def test_request_id_middleware():
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/test")
    def read_test():
        # verify the context variable is set
        assert request_id_var.get() != ""
        return {"ok": True}

    client = TestClient(app)
    response = client.get("/test")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    # Test setting custom X-Request-ID
    custom_id = "custom-uuid-123"
    response_custom = client.get("/test", headers={"X-Request-ID": custom_id})
    assert response_custom.headers["X-Request-ID"] == custom_id


def test_rate_limit_middleware():
    app = FastAPI()
    # set rate limit to 2 requests per minute
    app.add_middleware(RateLimitMiddleware, limit=2)

    @app.get("/test")
    def read_test():
        return {"ok": True}

    client = TestClient(app)
    # request 1
    res1 = client.get("/test")
    assert res1.status_code == 200
    # request 2
    res2 = client.get("/test")
    assert res2.status_code == 200
    # request 3 (rate limited)
    res3 = client.get("/test")
    assert res3.status_code == 429
    assert res3.json()["detail"] == "Too many requests. Rate limit exceeded."


def test_metrics_middleware():
    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/test-metrics")
    def read_test():
        return {"ok": True}

    client = TestClient(app)
    res = client.get("/test-metrics")
    assert res.status_code == 200

    # check prometheus metrics text
    metrics_str = metrics_registry.generate_prometheus_metrics()
    assert 'http_requests_total{method="GET",path="/test-metrics",status="200"}' in metrics_str
    assert "active_requests_count" in metrics_str


def test_logging_configuration():
    # Make sure calling configuration doesn't crash
    configure_logging(log_level="DEBUG", log_format="json")
    configure_logging(log_level="INFO", log_format="human")
