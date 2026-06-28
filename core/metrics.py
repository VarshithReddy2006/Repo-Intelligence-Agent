"""Lightweight Prometheus-compatible metrics registry."""

import threading
from typing import Dict, List, Tuple


class MetricsRegistry:
    """Collects and formats application metrics into Prometheus format."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        # (method, path, status) -> count
        self.http_requests_total: Dict[Tuple[str, str, int], int] = {}
        # (method, path, status) -> list of durations in seconds
        self.http_request_duration: Dict[Tuple[str, str, int], List[float]] = {}
        # active in-flight requests
        self.active_requests: int = 0
        # repository -> list of build durations in seconds
        self.build_durations: Dict[str, List[float]] = {}
        # (repository, task) -> list of durations in seconds
        self.analysis_task_duration: Dict[Tuple[str, str], List[float]] = {}

    def increment_request(self, method: str, path: str, status: int) -> None:
        with self.lock:
            key = (method, path, status)
            self.http_requests_total[key] = self.http_requests_total.get(key, 0) + 1

    def record_request_duration(self, method: str, path: str, status: int, duration_seconds: float) -> None:
        with self.lock:
            key = (method, path, status)
            if key not in self.http_request_duration:
                self.http_request_duration[key] = []
            self.http_request_duration[key].append(duration_seconds)

    def increment_active_requests(self) -> None:
        with self.lock:
            self.active_requests += 1

    def decrement_active_requests(self) -> None:
        with self.lock:
            self.active_requests = max(0, self.active_requests - 1)

    def record_build_duration(self, repo_name: str, duration_seconds: float) -> None:
        with self.lock:
            if repo_name not in self.build_durations:
                self.build_durations[repo_name] = []
            self.build_durations[repo_name].append(duration_seconds)

    def record_task_duration(
        self, repo_name: str, task_name: str, duration_seconds: float
    ) -> None:
        with self.lock:
            key = (repo_name, task_name)
            if key not in self.analysis_task_duration:
                self.analysis_task_duration[key] = []
            self.analysis_task_duration[key].append(duration_seconds)

    def generate_prometheus_metrics(self) -> str:
        lines = []

        with self.lock:
            # 1. HTTP Request Total
            lines.append("# HELP http_requests_total Total number of HTTP requests.")
            lines.append("# TYPE http_requests_total counter")
            for (method, path, status), count in self.http_requests_total.items():
                lines.append(
                    f'http_requests_total{{method="{method}",path="{path}",status="{status}"}} {count}.0'
                )

            # 1b. HTTP Request Durations
            lines.append(
                "# HELP http_request_duration_seconds HTTP request latencies in seconds."
            )
            lines.append("# TYPE http_request_duration_seconds summary")
            for (method, path, status), durations in self.http_request_duration.items():
                total = sum(durations)
                count = len(durations)
                lines.append(
                    f'http_request_duration_seconds_sum{{method="{method}",path="{path}",status="{status}"}} {total:.6f}'
                )
                lines.append(
                    f'http_request_duration_seconds_count{{method="{method}",path="{path}",status="{status}"}} {count}'
                )

            # 2. Active Requests
            lines.append(
                "# HELP active_requests_count Total number of active requests."
            )
            lines.append("# TYPE active_requests_count gauge")
            lines.append(f"active_requests_count {self.active_requests}.0")

            # 3. Build Durations
            lines.append(
                "# HELP build_duration_seconds Build pipeline durations in seconds."
            )
            lines.append("# TYPE build_duration_seconds summary")
            for repo, durations in self.build_durations.items():
                total = sum(durations)
                count = len(durations)
                lines.append(
                    f'build_duration_seconds_sum{{repository="{repo}"}} {total:.6f}'
                )
                lines.append(
                    f'build_duration_seconds_count{{repository="{repo}"}} {count}'
                )

            # 4. Analysis Task Durations
            lines.append(
                "# HELP analysis_task_duration_seconds Duration of individual analysis tasks in seconds."
            )
            lines.append("# TYPE analysis_task_duration_seconds summary")
            for (repo, task), durations in self.analysis_task_duration.items():
                total = sum(durations)
                count = len(durations)
                lines.append(
                    f'analysis_task_duration_seconds_sum{{repository="{repo}",task="{task}"}} {total:.6f}'
                )
                lines.append(
                    f'analysis_task_duration_seconds_count{{repository="{repo}",task="{task}"}} {count}'
                )

        # 5. Cache Metrics from cache singleton
        from backend.dependencies import analysis_cache

        stats = analysis_cache.get_stats()

        lines.append("# HELP cache_hits_total Total number of analysis cache hits.")
        lines.append("# TYPE cache_hits_total counter")
        for key, count in stats.get("hits", {}).items():
            lines.append(f'cache_hits_total{{cache_key="{key}"}} {count}.0')

        lines.append("# HELP cache_misses_total Total number of analysis cache misses.")
        lines.append("# TYPE cache_misses_total counter")
        for key, count in stats.get("misses", {}).items():
            lines.append(f'cache_misses_total{{cache_key="{key}"}} {count}.0')

        lines.append(
            "# HELP cache_size Total number of entries currently in the cache."
        )
        lines.append("# TYPE cache_size gauge")
        lines.append(f"cache_size {stats.get('size', 0)}.0")

        return "\n".join(lines) + "\n"


# Metrics Registry Singleton
metrics_registry = MetricsRegistry()
