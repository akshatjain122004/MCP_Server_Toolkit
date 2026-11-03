import time
from collections import deque

from mcp.server.mcpserver.exceptions import ToolError


class RateLimiter:
    """Simple sliding-window rate limiter: at most `max_calls` per `period` seconds."""

    def __init__(self, max_calls: int, period: float):
        self.max_calls = max_calls
        self.period = period
        self._calls: deque[float] = deque()

    def allow(self) -> bool:
        now = time.monotonic()
        while self._calls and now - self._calls[0] > self.period:
            self._calls.popleft()
        if len(self._calls) >= self.max_calls:
            return False
        self._calls.append(now)
        return True

    def check(self) -> None:
        """Raise ToolError if this call would exceed the limit; else record it."""
        if not self.allow():
            raise ToolError(
                f"Rate limit exceeded: max {self.max_calls} calls per {self.period:.0f}s. "
                "Try again shortly."
            )


DEFAULT_TIMEOUT_SECONDS = 30
