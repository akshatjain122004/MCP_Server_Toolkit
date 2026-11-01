from common.limits import RateLimiter


def test_rate_limiter_blocks_after_max_calls():
    limiter = RateLimiter(max_calls=2, period=60)
    assert limiter.allow() is True
    assert limiter.allow() is True
    assert limiter.allow() is False
