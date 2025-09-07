"""Circuit breaker pattern implementation for external API resilience."""

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Circuit is open, rejecting calls
    HALF_OPEN = "half_open"  # Testing if service is back


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    def __init__(self, message: str = "Circuit breaker is open"):
        super().__init__(message)
        self.message = message


class CircuitBreaker:
    """
    Circuit breaker for protecting against cascading failures.

    Implements the circuit breaker pattern to prevent repeated calls
    to a failing service, allowing it time to recover.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] | tuple[type[Exception], ...] = Exception,
        name: str = "CircuitBreaker",
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again (half-open)
            expected_exception: Exception type or tuple of types that trigger circuit breaker
            name: Name for logging purposes
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name

        # State tracking
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time: datetime | None = None
        self.next_attempt_time: datetime | None = None

        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Call a function through the circuit breaker.

        Args:
            func: Function to call
            *args: Positional arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the function call

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Any exception raised by the function
        """
        async with self._lock:
            await self._check_state()

            if self.state == CircuitState.OPEN:
                logger.warning(f"Circuit breaker {self.name} is open, rejecting call")
                raise CircuitBreakerOpenError(
                    f"Circuit breaker {self.name} is open. Next attempt at {self.next_attempt_time}"
                )

            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                await self._on_success()
                return result

            except self.expected_exception as e:
                await self._on_failure()
                raise e

    async def _check_state(self) -> None:
        """Check and update circuit breaker state."""
        now = datetime.now()

        if self.state == CircuitState.OPEN:
            if self.next_attempt_time and now >= self.next_attempt_time:
                self.state = CircuitState.HALF_OPEN
                logger.info(f"Circuit breaker {self.name} moved to half-open state")

        elif self.state == CircuitState.HALF_OPEN:
            # Will attempt the call and see if it succeeds
            pass

    async def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            logger.info(f"Circuit breaker {self.name} recovered, closing circuit")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.last_failure_time = None
            self.next_attempt_time = None

    async def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        logger.warning(
            f"Circuit breaker {self.name} failure {self.failure_count}/{self.failure_threshold}"
        )

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.next_attempt_time = datetime.now() + timedelta(seconds=self.recovery_timeout)

            logger.error(
                f"Circuit breaker {self.name} opened due to {self.failure_count} failures. "
                f"Next attempt at {self.next_attempt_time}"
            )

    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)."""
        return self.state == CircuitState.CLOSED

    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting calls)."""
        return self.state == CircuitState.OPEN

    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)."""
        return self.state == CircuitState.HALF_OPEN

    def get_status(self) -> dict[str, Any]:
        """Get current circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "last_failure_time": self.last_failure_time.isoformat()
            if self.last_failure_time
            else None,
            "next_attempt_time": self.next_attempt_time.isoformat()
            if self.next_attempt_time
            else None,
            "recovery_timeout": self.recovery_timeout,
        }
    
    async def __aenter__(self) -> "CircuitBreaker":
        """Enter async context manager."""
        async with self._lock:
            await self._check_state()
            if self.state == CircuitState.OPEN:
                logger.warning(f"Circuit breaker {self.name} is open, rejecting call")
                raise CircuitBreakerOpenError(
                    f"Circuit breaker {self.name} is open. Next attempt at {self.next_attempt_time}"
                )
        return self
    
    async def __aexit__(self, exc_type: type[Exception] | None, exc_val: Exception | None, exc_tb: Any) -> bool:
        """Exit async context manager."""
        async with self._lock:
            if exc_type is None:
                await self._on_success()
            elif issubclass(exc_type, self.expected_exception):
                await self._on_failure()
        return False  # Don't suppress exceptions
