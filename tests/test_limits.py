import time

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from common.limits import RateLimiter


def test_rate_limiter_blocks_after_max_calls():
    limiter = RateLimiter(max_calls=2, period=60)
    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is False


def test_check_raises_tool_error_after_max_calls():
    limiter = RateLimiter(max_calls=2, period=60)
    limiter.check()
    limiter.check()
    with pytest.raises(ToolError):
        limiter.check()


def test_check_recovers_after_the_window_passes():
    limiter = RateLimiter(max_calls=1, period=0.05)
    limiter.check()
    with pytest.raises(ToolError):
        limiter.check()
    time.sleep(0.06)
    limiter.check()  # does not raise: the window has rolled past the first call
