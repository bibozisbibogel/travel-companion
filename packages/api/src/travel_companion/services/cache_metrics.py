"""Cache metrics tracking for monitoring and performance analysis."""

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class CacheMetrics:
    """Metrics for cache hit/miss tracking."""

    hits: int = 0
    misses: int = 0
    total_requests: int = 0
    hit_rate: float = 0.0
    miss_rate: float = 0.0
    last_reset: datetime = field(default_factory=lambda: datetime.now(UTC))

    def record_hit(self) -> None:
        """Record a cache hit."""
        self.hits += 1
        self.total_requests += 1
        self._update_rates()

    def record_miss(self) -> None:
        """Record a cache miss."""
        self.misses += 1
        self.total_requests += 1
        self._update_rates()

    def _update_rates(self) -> None:
        """Update hit and miss rates."""
        if self.total_requests > 0:
            self.hit_rate = (self.hits / self.total_requests) * 100
            self.miss_rate = (self.misses / self.total_requests) * 100

    def reset(self) -> None:
        """Reset all metrics."""
        self.hits = 0
        self.misses = 0
        self.total_requests = 0
        self.hit_rate = 0.0
        self.miss_rate = 0.0
        self.last_reset = datetime.now(UTC)

    def to_dict(self) -> dict[str, int | float | str]:
        """Convert metrics to dictionary for logging/API responses."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total_requests": self.total_requests,
            "hit_rate": round(self.hit_rate, 2),
            "miss_rate": round(self.miss_rate, 2),
            "last_reset": self.last_reset.isoformat(),
        }


class PerformanceTimer:
    """Context manager for timing operations."""

    def __init__(self, operation_name: str):
        """
        Initialize timer.

        Args:
            operation_name: Name of operation being timed
        """
        self.operation_name = operation_name
        self.start_time: float = 0
        self.end_time: float = 0
        self.duration_ms: float = 0

    def __enter__(self) -> "PerformanceTimer":
        """Start timing."""
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, *args: object) -> None:
        """Stop timing and log duration."""
        self.end_time = time.perf_counter()
        self.duration_ms = (self.end_time - self.start_time) * 1000

        logger.debug(
            f"{self.operation_name} completed",
            extra={
                "operation": self.operation_name,
                "duration_ms": round(self.duration_ms, 2),
            },
        )


@dataclass
class GeocodingMetrics:
    """Comprehensive geocoding service metrics."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    pending_requests: int = 0
    cache_metrics: CacheMetrics = field(default_factory=CacheMetrics)
    average_response_time_ms: float = 0.0
    _response_times: list[float] = field(default_factory=list)
    errors_by_type: dict[str, int] = field(
        default_factory=lambda: {
            "ZERO_RESULTS": 0,
            "OVER_QUERY_LIMIT": 0,
            "REQUEST_DENIED": 0,
            "INVALID_REQUEST": 0,
            "TIMEOUT": 0,
            "UNKNOWN": 0,
        }
    )

    def record_request(
        self,
        status: Literal["success", "failed", "pending"],
        response_time_ms: float,
        error_type: str | None = None,
        cache_hit: bool = False,
    ) -> None:
        """
        Record a geocoding request.

        Args:
            status: Request status (success, failed, pending)
            response_time_ms: Response time in milliseconds
            error_type: Type of error if request failed
            cache_hit: Whether result was served from cache
        """
        self.total_requests += 1

        if status == "success":
            self.successful_requests += 1
        elif status == "failed":
            self.failed_requests += 1
            if error_type and error_type in self.errors_by_type:
                self.errors_by_type[error_type] += 1
            else:
                self.errors_by_type["UNKNOWN"] += 1
        elif status == "pending":
            self.pending_requests += 1

        # Track cache hit/miss
        if cache_hit:
            self.cache_metrics.record_hit()
        else:
            self.cache_metrics.record_miss()

        # Update response time average
        self._response_times.append(response_time_ms)
        # Keep only last 1000 response times to prevent memory growth
        if len(self._response_times) > 1000:
            self._response_times = self._response_times[-1000:]
        self.average_response_time_ms = sum(self._response_times) / len(self._response_times)

    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.successful_requests / self.total_requests) * 100

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.failed_requests / self.total_requests) * 100

    def to_dict(self) -> dict[str, int | float | str | dict[str, int]]:
        """Convert metrics to dictionary for API responses."""
        return {
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "pending_requests": self.pending_requests,
            "success_rate": round(self.success_rate, 2),
            "failure_rate": round(self.failure_rate, 2),
            "average_response_time_ms": round(self.average_response_time_ms, 2),
            "cache_hit_rate": round(self.cache_metrics.hit_rate, 2),
            "errors_by_type": self.errors_by_type,
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.pending_requests = 0
        self.cache_metrics.reset()
        self.average_response_time_ms = 0.0
        self._response_times = []
        self.errors_by_type = {
            "ZERO_RESULTS": 0,
            "OVER_QUERY_LIMIT": 0,
            "REQUEST_DENIED": 0,
            "INVALID_REQUEST": 0,
            "TIMEOUT": 0,
            "UNKNOWN": 0,
        }
