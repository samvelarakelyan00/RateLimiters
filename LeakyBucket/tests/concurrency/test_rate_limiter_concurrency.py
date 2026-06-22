# Standard libs
import asyncio

# Non-Standard libs
import pytest

# Own Modules
from core.security.rate_limiter.rate_limiter import LeakyBucketLimiter
from core.security.rate_limiter.redis_client import redis_client


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

    assert sum(r is False for r in results) == 1
    assert sum(r is True for r in results) == 99


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

    assert sum(r is False for r in results) == 5
    assert sum(r is True for r in results) == 95


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

    assert sum(r is False for r in results) == 10
    assert sum(r is True for r in results) == 990


# --------------------------------------------------------------------------------------
# Different Keys
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

    assert sum(r is False for r in results) == 100


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

    assert sum(r is False for r in results) == 1000


# --------------------------------------------------------------------------------------
# Redis State Consistency
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

    bucket = await redis_client.hgetall("user")

    assert float(bucket["water_level"]) <= 3


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

    assert await redis_client.exists("user") == 1


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

    assert len(await redis_client.keys("user_*")) == 100


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

    assert sum(r is False for r in results) == 100


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

    assert sum(r is False for r in results) == 50


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