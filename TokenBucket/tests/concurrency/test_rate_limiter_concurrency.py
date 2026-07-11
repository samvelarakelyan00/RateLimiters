# Standard libs
import asyncio

# Non-Standard libs
import pytest

# Own Modules
from core.security.rate_limiter.rate_limiter import TokenBucket


async def get_tokens(client, key):
    raw_data = await client.get(key)
    if raw_data is None:
        return None
    tokens, last_update = raw_data.split(":")
    return float(tokens)


# --------------------------------------------------------------------------------------
# Same Key Concurrency
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_same_key_capacity_one_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=1.0, refill_rate=0.0)

    async def worker():
        return await limiter.acquire("docker_concurrency_user")

    results = await asyncio.gather(*[worker() for _ in range(100)])

    assert sum(r is True for r in results) == 1
    assert sum(r is False for r in results) == 99

    tokens = await get_tokens(test_redis_client, "docker_concurrency_user")
    assert tokens == pytest.approx(0.0, abs=1e-2)


@pytest.mark.asyncio
async def test_same_key_capacity_five_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=5.0, refill_rate=0.0)

    async def worker():
        return await limiter.acquire("docker_concurrency_user")

    results = await asyncio.gather(*[worker() for _ in range(100)])

    assert sum(r is True for r in results) == 5
    assert sum(r is False for r in results) == 95

    tokens = await get_tokens(test_redis_client, "docker_concurrency_user")
    assert tokens == pytest.approx(0.0, abs=1e-2)


@pytest.mark.asyncio
async def test_same_key_capacity_ten_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=10.0, refill_rate=0.0)

    async def worker():
        return await limiter.acquire("docker_concurrency_user")

    results = await asyncio.gather(*[worker() for _ in range(1000)])

    assert sum(r is True for r in results) == 10
    assert sum(r is False for r in results) == 990

    tokens = await get_tokens(test_redis_client, "docker_concurrency_user")
    assert tokens == pytest.approx(0.0, abs=1e-2)


# --------------------------------------------------------------------------------------
# Different Keys
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_different_keys_all_allowed_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=1.0, refill_rate=0.0)

    async def worker(index: int):
        return await limiter.acquire(f"docker_user_{index}")

    results = await asyncio.gather(*[worker(i) for i in range(100)])

    assert sum(r is True for r in results) == 100

    for i in range(100):
        tokens = await get_tokens(test_redis_client, f"docker_user_{i}")
        assert tokens == pytest.approx(0.0, abs=1e-2)


@pytest.mark.asyncio
async def test_many_unique_keys_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=1.0, refill_rate=0.0)

    async def worker(index: int):
        return await limiter.acquire(f"docker_user_{index}")

    results = await asyncio.gather(*[worker(i) for i in range(1000)])

    assert sum(r is True for r in results) == 1000


# --------------------------------------------------------------------------------------
# Redis State Consistency
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_bucket_tokens_never_exceeds_capacity_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=3.0, refill_rate=0.0)

    async def worker():
        return await limiter.acquire("docker_concurrency_user")

    await asyncio.gather(*[worker() for _ in range(100)])

    tokens = await get_tokens(test_redis_client, "docker_concurrency_user")
    assert tokens <= 3.0
    assert tokens >= 0.0


@pytest.mark.asyncio
async def test_bucket_created_once_for_same_key_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=5.0, refill_rate=0.0)

    async def worker():
        return await limiter.acquire("docker_concurrency_user")

    await asyncio.gather(*[worker() for _ in range(100)])

    assert await test_redis_client.exists("docker_concurrency_user") == 1


@pytest.mark.asyncio
async def test_bucket_count_matches_unique_keys_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=1.0, refill_rate=0.0)

    async def worker(index: int):
        return await limiter.acquire(f"docker_user_{index}")

    await asyncio.gather(*[worker(i) for i in range(100)])

    keys = await test_redis_client.keys("docker_user_*")
    assert len(keys) == 100


# --------------------------------------------------------------------------------------
# Lock Verification - No Race Conditions
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_no_double_allow_when_capacity_one_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=1.0, refill_rate=0.0)

    async def worker():
        return await limiter.acquire("race_key")

    results = await asyncio.gather(*[worker() for _ in range(500)])

    assert results.count(True) == 1
    assert results.count(False) == 499

    tokens = await get_tokens(test_redis_client, "race_key")
    assert tokens == pytest.approx(0.0, abs=1e-2)


@pytest.mark.asyncio
async def test_no_double_allow_when_capacity_two_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=2.0, refill_rate=0.0)

    async def worker():
        return await limiter.acquire("race_key")

    results = await asyncio.gather(*[worker() for _ in range(500)])

    assert results.count(True) == 2
    assert results.count(False) == 498

    tokens = await get_tokens(test_redis_client, "race_key")
    assert tokens == pytest.approx(0.0, abs=1e-2)


# --------------------------------------------------------------------------------------
# Token Bucket Specific Concurrency Tests
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_concurrent_refill_and_consume(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=10.0, refill_rate=1.0)

    async def worker(worker_id: int):
        result1 = await limiter.acquire(f"concurrent_user")
        await asyncio.sleep(0.1)
        result2 = await limiter.acquire(f"concurrent_user")
        return result1, result2

    results = await asyncio.gather(*[worker(i) for i in range(10)])

    first_results = [r[0] for r in results]
    assert sum(first_results) == 10

    second_results = [r[1] for r in results]
    assert sum(second_results) >= 0


@pytest.mark.asyncio
async def test_concurrent_burst_consumption(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=10.0, refill_rate=1.0)

    async def worker():
        return await limiter.acquire("burst_user")

    results = await asyncio.gather(*[worker() for _ in range(100)])

    assert results.count(True) == 10
    assert results.count(False) == 90

    await asyncio.sleep(2.0)

    results2 = await asyncio.gather(*[worker() for _ in range(10)])
    assert results2.count(True) >= 1


@pytest.mark.asyncio
async def test_concurrent_different_endpoints(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=2.0, refill_rate=0.0)

    from core.security.rate_limiter.rate_limit_service import RateLimitService

    login_key = RateLimitService.build_email_key("login", "test@example.com")
    signup_key = RateLimitService.build_email_key("signup", "test@example.com")

    async def login_worker():
        return await limiter.acquire(login_key)

    async def signup_worker():
        return await limiter.acquire(signup_key)

    login_tasks = [login_worker() for _ in range(5)]
    signup_tasks = [signup_worker() for _ in range(5)]

    all_results = await asyncio.gather(*(login_tasks + signup_tasks))

    login_results = all_results[:5]
    signup_results = all_results[5:]

    assert login_results.count(True) == 2
    assert login_results.count(False) == 3
    assert signup_results.count(True) == 2
    assert signup_results.count(False) == 3