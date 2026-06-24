# Standard libs
import asyncio

# Non-Standard libs
import pytest

# Own Modules
from core.security.rate_limiter.rate_limiter import LeakyBucket


# --------------------------------------------------------------------------------------
# Same Key Concurrency
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_same_key_capacity_one_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=0.0)

    async def worker():
        return await limiter.acquire("docker_concurrency_user")

    results = await asyncio.gather(*[worker() for _ in range(100)])

    assert sum(r is True for r in results) == 1
    assert sum(r is False for r in results) == 99

    stored_user = await test_redis_client.hgetall("docker_concurrency_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)



@pytest.mark.asyncio
async def test_same_key_capacity_five_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=5.0, leak_rate=0.0)

    async def worker():
        return await limiter.acquire("docker_concurrency_user")

    results = await asyncio.gather(*[worker() for _ in range(100)])

    assert sum(r is True for r in results) == 5
    assert sum(r is False for r in results) == 95

    stored_user = await test_redis_client.hgetall("docker_concurrency_user")
    assert float(stored_user["water_level"]) == pytest.approx(5.0, abs=1e-2)


@pytest.mark.asyncio
async def test_same_key_capacity_ten_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=10.0, leak_rate=0.0)

    async def worker():
        return await limiter.acquire("docker_concurrency_user")

    results = await asyncio.gather(*[worker() for _ in range(1000)])

    assert sum(r is True for r in results) == 10
    assert sum(r is False for r in results) == 990

    stored_user = await test_redis_client.hgetall("docker_concurrency_user")
    assert float(stored_user["water_level"]) == pytest.approx(10.0, abs=1e-2)


# --------------------------------------------------------------------------------------
# Different Keys
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_different_keys_all_allowed_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=0.0)

    async def worker(index: int):
        return await limiter.acquire(f"docker_user_{index}")

    results = await asyncio.gather(*[worker(i) for i in range(100)])

    assert sum(r is True for r in results) == 100

    for i in range(100):
        stored_user = await test_redis_client.hgetall(f"docker_user_{i}")
        assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)


@pytest.mark.asyncio
async def test_many_unique_keys_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=0.0)

    async def worker(index: int):
        return await limiter.acquire(f"docker_user_{index}")

    results = await asyncio.gather(*[worker(i) for i in range(1000)])

    assert sum(r is True for r in results) == 1000


# --------------------------------------------------------------------------------------
# Redis State Consistency
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_bucket_water_level_never_exceeds_capacity_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=3.0, leak_rate=0.0)

    async def worker():
        return await limiter.acquire("docker_concurrency_user")

    await asyncio.gather(*[worker() for _ in range(100)])

    bucket = await test_redis_client.hgetall("docker_concurrency_user")

    assert float(bucket["water_level"]) <= 3.0


@pytest.mark.asyncio
async def test_bucket_created_once_for_same_key_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=5.0, leak_rate=0.0)

    async def worker():
        return await limiter.acquire("docker_concurrency_user")

    await asyncio.gather(*[worker() for _ in range(100)])

    assert await test_redis_client.exists("docker_concurrency_user") == 1


@pytest.mark.asyncio
async def test_bucket_count_matches_unique_keys_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=0.0)

    async def worker(index: int):
        return await limiter.acquire(f"docker_user_{index}")

    await asyncio.gather(*[worker(i) for i in range(100)])

    keys = await test_redis_client.keys("docker_user_*")
    assert len(keys) == 100


# --------------------------------------------------------------------------------------
# Stress Tests
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_ten_thousand_concurrent_requests_stress(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=100.0, leak_rate=0.0)

    async def worker():
        return await limiter.acquire("docker_stress_user")

    results = await asyncio.gather(*[worker() for _ in range(10000)])

    assert sum(r is True for r in results) == 100
    assert sum(r is False for r in results) == 9900

    stored_user = await test_redis_client.hgetall("docker_stress_user")
    assert float(stored_user["water_level"]) == pytest.approx(100.0, abs=1e-2)


""" ============================ TimeoutError =================================
            redis.exceptions.TimeoutError: Timeout connecting to server

# @pytest.mark.asyncio
# async def test_fifty_thousand_requests_same_key_stress(test_redis_client, monkeypatch) -> None:
#     monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)
# 
#     limiter = LeakyBucket(capacity=50.0, leak_rate=0.0)
# 
#     async def worker():
#         return await limiter.acquire("docker_stress_user")
# 
#     results = await asyncio.gather(*[worker() for _ in range(50000)])
# 
#     assert sum(r is True for r in results) == 50
#     assert sum(r is False for r in results) == 49950
# 
#     stored_user = await test_redis_client.hgetall("docker_stress_user")
#     assert float(stored_user["water_level"]) == pytest.approx(50.0, abs=1e-2)
"""


# --------------------------------------------------------------------------------------
# Lock Verification
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_no_double_allow_when_capacity_one_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=0.0)

    async def worker():
        return await limiter.acquire("race_key")

    results = await asyncio.gather(*[worker() for _ in range(500)])

    assert results.count(True) == 1
    assert results.count(False) == 499

    stored_user = await test_redis_client.hgetall("race_key")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)


@pytest.mark.asyncio
async def test_no_double_allow_when_capacity_two_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=2.0, leak_rate=0.0)

    async def worker():
        return await limiter.acquire("race_key")

    results = await asyncio.gather(*[worker() for _ in range(500)])

    assert results.count(True) == 2
    assert results.count(False) == 498

    stored_user = await test_redis_client.hgetall("race_key")
    assert float(stored_user["water_level"]) == pytest.approx(2.0, abs=1e-2)
