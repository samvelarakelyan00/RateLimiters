# Standard libs
import asyncio

# Non-Standard libs
import pytest

# Own Modules
from core.security.rate_limiter import LeakyBucketLimiter


# --------------------------------------------------------------------------------------
# Same Key Concurrency
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_same_key_capacity_one() -> None:
    limiter = LeakyBucketLimiter(
        capacity=1,
        leak_rate=0.0
    )

    async def worker():
        return await limiter.acquire("user")

    results = await asyncio.gather(
        *[worker() for _ in range(100)]
    )

    allowed = sum(result is False for result in results)
    blocked = sum(result is True for result in results)

    assert allowed == 1
    assert blocked == 99


@pytest.mark.asyncio
async def test_same_key_capacity_five() -> None:
    limiter = LeakyBucketLimiter(
        capacity=5,
        leak_rate=0.0
    )

    async def worker():
        return await limiter.acquire("user")

    results = await asyncio.gather(
        *[worker() for _ in range(100)]
    )

    allowed = sum(result is False for result in results)
    blocked = sum(result is True for result in results)

    assert allowed == 5
    assert blocked == 95


@pytest.mark.asyncio
async def test_same_key_capacity_ten() -> None:
    limiter = LeakyBucketLimiter(
        capacity=10,
        leak_rate=0.0
    )

    async def worker():
        return await limiter.acquire("user")

    results = await asyncio.gather(
        *[worker() for _ in range(1000)]
    )

    allowed = sum(result is False for result in results)
    blocked = sum(result is True for result in results)

    assert allowed == 10
    assert blocked == 990


# --------------------------------------------------------------------------------------
# Different Keys Concurrency
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_different_keys_all_allowed() -> None:
    limiter = LeakyBucketLimiter(
        capacity=1,
        leak_rate=0.0
    )

    async def worker(index: int):
        return await limiter.acquire(f"user_{index}")

    results = await asyncio.gather(
        *[worker(i) for i in range(100)]
    )

    allowed = sum(result is False for result in results)

    assert allowed == 100


@pytest.mark.asyncio
async def test_many_unique_keys() -> None:
    limiter = LeakyBucketLimiter(
        capacity=1,
        leak_rate=0.0
    )

    async def worker(index: int):
        return await limiter.acquire(f"user_{index}")

    results = await asyncio.gather(
        *[worker(i) for i in range(1000)]
    )

    allowed = sum(result is False for result in results)

    assert allowed == 1000


# --------------------------------------------------------------------------------------
# State Consistency
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_bucket_water_level_never_exceeds_capacity() -> None:
    limiter = LeakyBucketLimiter(
        capacity=3,
        leak_rate=0.0
    )

    async def worker():
        return await limiter.acquire("user")

    await asyncio.gather(
        *[worker() for _ in range(100)]
    )

    water_level, _ = limiter._buckets["user"]

    assert water_level <= 3


@pytest.mark.asyncio
async def test_bucket_created_once_for_same_key() -> None:
    limiter = LeakyBucketLimiter(
        capacity=5,
        leak_rate=0.0
    )

    async def worker():
        return await limiter.acquire("user")

    await asyncio.gather(
        *[worker() for _ in range(100)]
    )

    assert len(limiter._buckets) == 1


@pytest.mark.asyncio
async def test_bucket_count_matches_unique_keys() -> None:
    limiter = LeakyBucketLimiter(
        capacity=1,
        leak_rate=0.0
    )

    async def worker(index: int):
        return await limiter.acquire(f"user_{index}")

    await asyncio.gather(
        *[worker(i) for i in range(100)]
    )

    assert len(limiter._buckets) == 100


# --------------------------------------------------------------------------------------
# Stress Tests
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ten_thousand_concurrent_requests() -> None:
    limiter = LeakyBucketLimiter(
        capacity=100,
        leak_rate=0.0
    )

    async def worker():
        return await limiter.acquire("user")

    results = await asyncio.gather(
        *[worker() for _ in range(10000)]
    )

    allowed = sum(result is False for result in results)

    assert allowed == 100


@pytest.mark.asyncio
async def test_fifty_thousand_requests_same_key() -> None:
    limiter = LeakyBucketLimiter(
        capacity=50,
        leak_rate=0.0
    )

    async def worker():
        return await limiter.acquire("user")

    results = await asyncio.gather(
        *[worker() for _ in range(50000)]
    )

    allowed = sum(result is False for result in results)

    assert allowed == 50


# --------------------------------------------------------------------------------------
# Lock Verification
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_no_double_allow_when_capacity_one() -> None:
    limiter = LeakyBucketLimiter(
        capacity=1,
        leak_rate=0.0
    )

    async def worker():
        return await limiter.acquire("race_key")

    results = await asyncio.gather(
        *[worker() for _ in range(500)]
    )

    assert results.count(False) == 1


@pytest.mark.asyncio
async def test_no_double_allow_when_capacity_two() -> None:
    limiter = LeakyBucketLimiter(
        capacity=2,
        leak_rate=0.0
    )

    async def worker():
        return await limiter.acquire("race_key")

    results = await asyncio.gather(
        *[worker() for _ in range(500)]
    )

    assert results.count(False) == 2