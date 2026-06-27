"""Production security middlewares including configurable rate limiting."""

import time
import threading
from collections import defaultdict
from typing import Dict, List
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response, JSONResponse


class RateLimiter:
    """Thread-safe sliding-window rate limiter for clients."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.requests: Dict[str, List[float]] = defaultdict(list)
        self.lock = threading.Lock()

    def is_allowed(self, client_ip: str) -> bool:
        if self.limit <= 0:
            return True

        now = time.time()
        with self.lock:
            # Prune requests older than 60 seconds
            self.requests[client_ip] = [
                t for t in self.requests[client_ip] if now - t < 60
            ]

            if len(self.requests[client_ip]) < self.limit:
                self.requests[client_ip].append(now)
                # Remove the key entirely when the window is empty after pruning
                # to prevent unbounded memory growth as unique IPs accumulate.
                if not self.requests[client_ip]:
                    del self.requests[client_ip]
                return True
            return False


class RateLimitMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware enforcing request rate limiting per IP address."""

    def __init__(self, app, limit: int = 60) -> None:
        super().__init__(app)
        self.limiter = RateLimiter(limit)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Bypass rate limit on health/metrics routes
        if request.url.path in [
            "/health",
            "/metrics",
            "/api/v1/health",
            "/api/v1/metrics",
        ]:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        if not self.limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Rate limit exceeded."},
            )

        return await call_next(request)
