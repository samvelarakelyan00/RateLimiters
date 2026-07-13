# Standard libs
import asyncio

# Non-Standard libs
import pytest

# Own Modules
from core.security.rate_limiter.rate_limiter import FixedWindowCounter


# Helper to get count from Redis String storage
async def get_window_count(client, key):
    raw_data = await client.get(key)
    if raw_data is None:
        return None
    return int(raw_data)


# Helper to get current window key for a given search_key
def get_current_window_key(search_key: str, window_size: float) -> str:
    import time
    now = time.time()
    window_id = int(now // window_size)
    return f"{search_key}:{window_id}"


# --------------------------------------------------------------------------------------
# Same Key Concurrency
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_same_key_limit_one_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    async def worker():
        return await limiter.acquire("docker_concurrency_user")

    results = await asyncio.gather(*[worker() for _ in range(100)])

    assert sum(r is True for r in results) == 1
    assert sum(r is False for r in results) == 99

    key = get_current_window_key("docker_concurrency_user", 60.0)
    count = await get_window_count(test_redis_client, key)
    assert count == 1


@pytest.mark.asyncio
async def test_same_key_limit_five_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=5)

    async def worker():
        return await limiter.acquire("docker_concurrency_user")

    results = await asyncio.gather(*[worker() for _ in range(100)])

    assert sum(r is True for r in results) == 5
    assert sum(r is False for r in results) == 95

    key = get_current_window_key("docker_concurrency_user", 60.0)
    count = await get_window_count(test_redis_client, key)
    assert count == 5


@pytest.mark.asyncio
async def test_same_key_limit_ten_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=10)

    async def worker():
        return await limiter.acquire("docker_concurrency_user")

    results = await asyncio.gather(*[worker() for _ in range(1000)])

    assert sum(r is True for r in results) == 10
    assert sum(r is False for r in results) == 990

    key = get_current_window_key("docker_concurrency_user", 60.0)
    count = await get_window_count(test_redis_client, key)
    assert count == 10


# --------------------------------------------------------------------------------------
# Different Keys
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_different_keys_all_allowed_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    async def worker(index: int):
        return await limiter.acquire(f"docker_user_{index}")

    results = await asyncio.gather(*[worker(i) for i in range(100)])

    assert sum(r is True for r in results) == 100

    for i in range(100):
        key = get_current_window_key(f"docker_user_{i}", 60.0)
        count = await get_window_count(test_redis_client, key)
        assert count == 1


@pytest.mark.asyncio
async def test_many_unique_keys_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    async def worker(index: int):
        return await limiter.acquire(f"docker_user_{index}")

    results = await asyncio.gather(*[worker(i) for i in range(1000)])

    assert sum(r is True for r in results) == 1000


# --------------------------------------------------------------------------------------
# Redis State Consistency
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_bucket_count_never_exceeds_limit_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=3)

    async def worker():
        return await limiter.acquire("docker_concurrency_user")

    await asyncio.gather(*[worker() for _ in range(100)])

    key = get_current_window_key("docker_concurrency_user", 60.0)
    count = await get_window_count(test_redis_client, key)
    assert count <= 3
    assert count >= 0


@pytest.mark.asyncio
async def test_bucket_created_once_for_same_key_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=5)

    async def worker():
        return await limiter.acquire("docker_concurrency_user")

    await asyncio.gather(*[worker() for _ in range(100)])

    key = get_current_window_key("docker_concurrency_user", 60.0)
    assert await test_redis_client.exists(key) == 1


@pytest.mark.asyncio
async def test_bucket_count_matches_unique_keys_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    async def worker(index: int):
        return await limiter.acquire(f"docker_user_{index}")

    await asyncio.gather(*[worker(i) for i in range(100)])

    keys = await test_redis_client.keys("docker_user_*")
    assert len(keys) == 100


# --------------------------------------------------------------------------------------
# Lock Verification - No Race Conditions
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_no_double_allow_when_limit_one_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    async def worker():
        return await limiter.acquire("race_key")

    results = await asyncio.gather(*[worker() for _ in range(500)])

    assert results.count(True) == 1
    assert results.count(False) == 499

    key = get_current_window_key("race_key", 60.0)
    count = await get_window_count(test_redis_client, key)
    assert count == 1


@pytest.mark.asyncio
async def test_no_double_allow_when_limit_two_concurrency(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=2)

    async def worker():
        return await limiter.acquire("race_key")

    results = await asyncio.gather(*[worker() for _ in range(500)])

    assert results.count(True) == 2
    assert results.count(False) == 498

    key = get_current_window_key("race_key", 60.0)
    count = await get_window_count(test_redis_client, key)
    assert count == 2


# --------------------------------------------------------------------------------------
# Fixed Window Specific Concurrency Tests
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_concurrent_window_reset(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=2.0, limit=5)

    async def worker():
        return await limiter.acquire("window_reset_user")

    # Fill the window
    results1 = await asyncio.gather(*[worker() for _ in range(5)])
    assert results1.count(True) == 5

    # Try more - should be blocked
    results2 = await asyncio.gather(*[worker() for _ in range(5)])
    assert results2.count(True) == 0

    # Wait for window to expire
    await asyncio.sleep(2.1)

    # New window should allow requests
    results3 = await asyncio.gather(*[worker() for _ in range(5)])
    assert results3.count(True) == 5


@pytest.mark.asyncio
async def test_concurrent_different_window_sizes(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    small_window = FixedWindowCounter(window_size=2.0, limit=2)
    large_window = FixedWindowCounter(window_size=10.0, limit=5)

    async def small_worker():
        return await small_window.acquire("small_user")

    async def large_worker():
        return await large_window.acquire("large_user")

    small_results = await asyncio.gather(*[small_worker() for _ in range(10)])
    large_results = await asyncio.gather(*[large_worker() for _ in range(10)])

    # Small window: limit 2 per 2 seconds
    assert small_results.count(True) == 2
    assert small_results.count(False) == 8

    # Large window: limit 5 per 10 seconds
    assert large_results.count(True) == 5
    assert large_results.count(False) == 5


@pytest.mark.asyncio
async def test_concurrent_get_remaining(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=10)

    async def worker():
        return await limiter.acquire("remaining_user")

    # Consume 3 tokens
    await asyncio.gather(*[worker() for _ in range(3)])

    # Check remaining while concurrent requests are happening
    remaining = await limiter.get_remaining("remaining_user")
    assert remaining == 7

    # Consume 3 more
    await asyncio.gather(*[worker() for _ in range(3)])

    remaining = await limiter.get_remaining("remaining_user")
    assert remaining == 4


@pytest.mark.asyncio
async def test_concurrent_different_endpoints(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=2)

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