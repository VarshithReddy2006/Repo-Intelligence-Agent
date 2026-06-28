"""FastAPI middleware to capture HTTP request statistics for Prometheus metrics."""

import time
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from core.metrics import metrics_registry


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware collecting HTTP request telemetry."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Exclude metrics scraping itself from metrics collection to avoid noise
        if request.url.path in ["/metrics", "/api/v1/metrics"]:
            return await call_next(request)

        metrics_registry.increment_active_requests()
        start_time = time.time()

        try:
            response = await call_next(request)
            elapsed = time.time() - start_time
            # Increment request counter labeled by method, path, and status code
            metrics_registry.increment_request(
                request.method, request.url.path, response.status_code
            )
            metrics_registry.record_request_duration(
                request.method, request.url.path, response.status_code, elapsed
            )
            return response
        finally:
            metrics_registry.decrement_active_requests()
