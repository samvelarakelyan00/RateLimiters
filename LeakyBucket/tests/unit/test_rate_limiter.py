# Standard libs
import asyncio
from unittest.mock import patch

# Non-Standard libs
import pytest

# Own Modules
from core.security.rate_limiter import LeakyBucketLimiter


# --------------------------------------------------------------------------------------
# Basic Request Flow
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_first_request_is_allowed() -> None:
    limiter = LeakyBucketLimiter(capacity=3, leak_rate=1.0)

    result = await limiter.acquire("user")

    assert result is False


@pytest.mark.asyncio
async def test_second_request_is_allowed_before_capacity() -> None:
    limiter = LeakyBucketLimiter(capacity=3, leak_rate=1.0)

    await limiter.acquire("user")
    result = await limiter.acquire("user")

    assert result is False


@pytest.mark.asyncio
async def test_request_at_capacity_is_allowed() -> None:
    limiter = LeakyBucketLimiter(capacity=3, leak_rate=1.0)

    await limiter.acquire("user")
    await limiter.acquire("user")

    result = await limiter.acquire("user")

    assert result is False


@pytest.mark.asyncio
async def test_request_above_capacity_is_blocked() -> None:
    limiter = LeakyBucketLimiter(capacity=3, leak_rate=1.0)

    await limiter.acquire("user")
    await limiter.acquire("user")
    await limiter.acquire("user")

    result = await limiter.acquire("user")

    assert result is True


@pytest.mark.asyncio
async def test_multiple_requests_after_block_remain_blocked() -> None:
    limiter = LeakyBucketLimiter(capacity=1, leak_rate=0.0)

    await limiter.acquire("user")

    assert await limiter.acquire("user") is True
    assert await limiter.acquire("user") is True
    assert await limiter.acquire("user") is True


# --------------------------------------------------------------------------------------
# Key Isolation
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_different_keys_are_independent() -> None:
    limiter = LeakyBucketLimiter(capacity=1, leak_rate=0.0)

    assert await limiter.acquire("user_a") is False
    assert await limiter.acquire("user_b") is False


@pytest.mark.asyncio
async def test_same_key_uses_same_bucket() -> None:
    limiter = LeakyBucketLimiter(capacity=1, leak_rate=0.0)

    assert await limiter.acquire("user") is False
    assert await limiter.acquire("user") is True


@pytest.mark.asyncio
async def test_many_keys_do_not_interfere() -> None:
    limiter = LeakyBucketLimiter(capacity=1, leak_rate=0.0)

    for i in range(100):
        assert await limiter.acquire(f"user_{i}") is False


# --------------------------------------------------------------------------------------
# Leak Recovery
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
@patch('time.monotonic')
async def test_bucket_recovers_after_leak_period(mock_time) -> None:
    mock_time.return_value = 1000.0
    limiter = LeakyBucketLimiter(capacity=1, leak_rate=1.0)

    await limiter.acquire("user")

    # Fast-forward 1.1 seconds instantly without sleeping
    mock_time.return_value = 1001.1
    assert await limiter.acquire("user") is False


@pytest.mark.asyncio
async def test_partial_leak_does_not_fully_reset_bucket() -> None:
    limiter = LeakyBucketLimiter(capacity=2, leak_rate=1.0)

    await limiter.acquire("user")
    await limiter.acquire("user")

    await asyncio.sleep(0.9)

    assert await limiter.acquire("user") is False
    assert await limiter.acquire("user") is True


@pytest.mark.asyncio
@patch('time.monotonic')
async def test_partial_leak_does_not_fully_reset_bucket(mock_time) -> None:
    mock_time.return_value = 1000.0
    limiter = LeakyBucketLimiter(capacity=2, leak_rate=1.0)

    await limiter.acquire("user")
    await limiter.acquire("user")

    mock_time.return_value = 1000.5
    assert await limiter.acquire("user") is True

    mock_time.value = 1001.1
    assert await limiter.acquire("user") is False


@pytest.mark.asyncio
@patch('time.monotonic')
async def test_full_leak_empties_bucket(mock_time) -> None:
    mock_time.return_value = 1000.0
    limiter = LeakyBucketLimiter(capacity=2, leak_rate=2.0)

    await limiter.acquire("user")
    await limiter.acquire("user")

    mock_time.return_value = 1001.1
    assert await limiter.acquire("user") is False


@pytest.mark.asyncio
async def test_high_leak_rate_recovers_faster() -> None:
    limiter = LeakyBucketLimiter(capacity=1, leak_rate=10.0)

    await limiter.acquire("user")

    await asyncio.sleep(0.2)

    assert await limiter.acquire("user") is False


@pytest.mark.asyncio
async def test_low_leak_rate_recovers_slower() -> None:
    limiter = LeakyBucketLimiter(capacity=1, leak_rate=0.1)

    await limiter.acquire("user")

    await asyncio.sleep(0.2)

    assert await limiter.acquire("user") is True


# --------------------------------------------------------------------------------------
# Capacity Edge Cases
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_capacity_one_allows_single_request() -> None:
    limiter = LeakyBucketLimiter(capacity=1, leak_rate=1.0)

    assert await limiter.acquire("user") is False


@pytest.mark.asyncio
async def test_capacity_one_blocks_second_request() -> None:
    limiter = LeakyBucketLimiter(capacity=1, leak_rate=1.0)

    await limiter.acquire("user")

    assert await limiter.acquire("user") is True


@pytest.mark.asyncio
async def test_large_capacity_allows_many_requests() -> None:
    limiter = LeakyBucketLimiter(capacity=1000, leak_rate=0.0)

    for _ in range(1000):
        assert await limiter.acquire("user") is False


@pytest.mark.asyncio
async def test_large_capacity_blocks_after_limit() -> None:
    limiter = LeakyBucketLimiter(capacity=1000, leak_rate=0.0)

    for _ in range(1000):
        await limiter.acquire("user")

    assert await limiter.acquire("user") is True


# --------------------------------------------------------------------------------------
# Internal State Validation
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_bucket_created_after_first_request() -> None:
    limiter = LeakyBucketLimiter(capacity=1, leak_rate=1.0)

    await limiter.acquire("user")

    assert "user" in limiter._buckets


@pytest.mark.asyncio
async def test_bucket_stores_water_level() -> None:
    limiter = LeakyBucketLimiter(capacity=3, leak_rate=1.0)

    await limiter.acquire("user")

    water_level, _ = limiter._buckets["user"]

    assert water_level > 0


@pytest.mark.asyncio
async def test_water_level_never_negative() -> None:
    limiter = LeakyBucketLimiter(capacity=1, leak_rate=1000.0)

    await limiter.acquire("user")

    await asyncio.sleep(0.2)

    await limiter.acquire("user")

    water_level, _ = limiter._buckets["user"]

    assert water_level >= 0


# --------------------------------------------------------------------------------------
# Concurrency
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_concurrent_requests_respect_capacity() -> None:
    limiter = LeakyBucketLimiter(capacity=10, leak_rate=0.0)

    async def worker():
        return await limiter.acquire("user")

    results = await asyncio.gather(
        *[worker() for _ in range(100)]
    )

    allowed = sum(result is False for result in results)
    blocked = sum(result is True for result in results)

    assert allowed == 10
    assert blocked == 90


@pytest.mark.asyncio
async def test_concurrent_access_same_key_is_safe() -> None:
    limiter = LeakyBucketLimiter(capacity=1, leak_rate=0.0)

    async def worker():
        return await limiter.acquire("user")

    results = await asyncio.gather(
        *[worker() for _ in range(50)]
    )

    allowed = sum(result is False for result in results)
    blocked = sum(result is True for result in results)

    assert allowed == 1
    assert blocked == 49