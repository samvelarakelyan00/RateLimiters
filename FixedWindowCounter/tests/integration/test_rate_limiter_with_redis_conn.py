# Standard libs
import asyncio
import time

# Non-Standard libs
import pytest

# Own Modules
from core.security.rate_limiter.rate_limiter import FixedWindowCounter


# Helper function to get count from Redis String storage
async def get_window_count(client, key):
    """Get count from Redis String storage."""
    raw_data = await client.get(key)
    if raw_data is None:
        return None
    return int(raw_data)


# Helper to get current window key for a given search_key
def get_current_window_key(search_key: str, window_size: float) -> str:
    """Generate the current window key."""
    now = time.time()
    window_id = int(now // window_size)
    return f"{search_key}:{window_id}"


# --------------------------------------------------------------------------------------
# Basic Request Flow
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_first_request_is_allowed_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=3)

    result = await limiter.acquire("docker_user_1")
    assert result is True

    count = await get_window_count(test_redis_client, get_current_window_key("docker_user_1", 60.0))
    assert count == 1


@pytest.mark.asyncio
async def test_second_request_is_allowed_before_limit_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=3)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 1

    second_result = await limiter.acquire("docker_user")
    assert second_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 2


@pytest.mark.asyncio
async def test_fourth_request_exceeds_limit_and_is_denied_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=3)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 1

    second_result = await limiter.acquire("docker_user")
    assert second_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 2

    third_result = await limiter.acquire("docker_user")
    assert third_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 3

    fourth_result = await limiter.acquire("docker_user")
    assert fourth_result is False
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 3


@pytest.mark.asyncio
async def test_request_above_limit_is_blocked_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=3)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 1

    second_result = await limiter.acquire("docker_user")
    assert second_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 2

    third_result = await limiter.acquire("docker_user")
    assert third_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 3

    fourth_result = await limiter.acquire("docker_user")
    assert fourth_result is False
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 3

    fifth_result = await limiter.acquire("docker_user")
    assert fifth_result is False
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 3


@pytest.mark.asyncio
async def test_multiple_requests_after_block_remain_blocked_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 1

    second_result = await limiter.acquire("docker_user")
    assert second_result is False
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 1

    third_result = await limiter.acquire("docker_user")
    assert third_result is False
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 1

    fourth_result = await limiter.acquire("docker_user")
    assert fourth_result is False
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 1


# --------------------------------------------------------------------------------------
# Key Isolation
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_different_keys_are_independent_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    first_result = await limiter.acquire("docker_user_1")
    assert first_result is True
    count_1 = await get_window_count(test_redis_client, get_current_window_key("docker_user_1", 60.0))
    assert count_1 == 1

    second_result = await limiter.acquire("docker_user_2")
    assert second_result is True
    count_2 = await get_window_count(test_redis_client, get_current_window_key("docker_user_2", 60.0))
    assert count_2 == 1


@pytest.mark.asyncio
async def test_same_key_uses_same_bucket_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 1

    second_result = await limiter.acquire("docker_user")
    assert second_result is False
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 1


@pytest.mark.asyncio
async def test_many_keys_do_not_interfere_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    for i in range(100):
        key = f"docker_user_{i}"
        result = await limiter.acquire(key)
        assert result is True

        count = await get_window_count(test_redis_client, get_current_window_key(key, 60.0))
        assert count == 1


# --------------------------------------------------------------------------------------
# Window Recovery (Fixed Window specific)
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_bucket_recovers_after_window_expires_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=2.0, limit=1)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 2.0))
    assert count == 1

    await asyncio.sleep(2.1)

    second_result = await limiter.acquire("docker_user")
    assert second_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 2.0))
    assert count == 1


@pytest.mark.asyncio
async def test_partial_window_does_not_reset_bucket_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=5.0, limit=2)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 5.0))
    assert count == 1

    second_result = await limiter.acquire("docker_user")
    assert second_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 5.0))
    assert count == 2

    await asyncio.sleep(1.0)

    third_result = await limiter.acquire("docker_user")
    assert third_result is False
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 5.0))
    assert count == 2


@pytest.mark.asyncio
async def test_new_window_allows_requests_after_reset_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=2.0, limit=1)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 2.0))
    assert count == 1

    await asyncio.sleep(2.1)

    second_result = await limiter.acquire("docker_user")
    assert second_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 2.0))
    assert count == 1


# --------------------------------------------------------------------------------------
# Capacity Edge Cases
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_limit_one_allows_single_request_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    result = await limiter.acquire("docker_user")
    assert result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 1


@pytest.mark.asyncio
async def test_limit_one_blocks_second_request_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 1

    second_result = await limiter.acquire("docker_user")
    assert second_result is False
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 1


@pytest.mark.asyncio
async def test_large_limit_allows_many_requests_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=1000)

    for _ in range(1000):
        result = await limiter.acquire("docker_user")
        assert result is True

    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 1000


@pytest.mark.asyncio
async def test_large_limit_blocks_after_limit_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=1000)

    for _ in range(1000):
        await limiter.acquire("docker_user")

    result = await limiter.acquire("docker_user")
    assert result is False

    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 60.0))
    assert count == 1000


# --------------------------------------------------------------------------------------
# Redis State Validation
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_bucket_created_after_first_request_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    result = await limiter.acquire("docker_user")
    assert result is True

    key = get_current_window_key("docker_user", 60.0)
    key_exists = await test_redis_client.exists(key)
    assert key_exists == 1


@pytest.mark.asyncio
async def test_bucket_stores_count_level_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=3)

    result = await limiter.acquire("docker_user")
    assert result is True

    key = get_current_window_key("docker_user", 60.0)
    raw_data = await test_redis_client.get(key)
    assert raw_data is not None
    assert int(raw_data) > 0


@pytest.mark.asyncio
async def test_count_never_negative_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True

    second_result = await limiter.acquire("docker_user")
    assert second_result is False

    key = get_current_window_key("docker_user", 60.0)
    count = await get_window_count(test_redis_client, key)
    assert count >= 0


# --------------------------------------------------------------------------------------
# Fixed Window Specific Tests
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_different_window_sizes_work_correctly_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=2.0, limit=2)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 2.0))
    assert count == 1

    second_result = await limiter.acquire("docker_user")
    assert second_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 2.0))
    assert count == 2

    third_result = await limiter.acquire("docker_user")
    assert third_result is False
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 2.0))
    assert count == 2

    await asyncio.sleep(2.1)

    fourth_result = await limiter.acquire("docker_user")
    assert fourth_result is True
    count = await get_window_count(test_redis_client, get_current_window_key("docker_user", 2.0))
    assert count == 1


@pytest.mark.asyncio
async def test_get_remaining_returns_correct_value_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=10)

    for _ in range(3):
        await limiter.acquire("docker_user")

    remaining = await limiter.get_remaining("docker_user")
    assert remaining == 7


@pytest.mark.asyncio
async def test_get_remaining_returns_limit_for_new_key_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=10)

    remaining = await limiter.get_remaining("docker_user")
    assert remaining == 10


@pytest.mark.asyncio
async def test_reset_deletes_all_keys_for_search_key_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = FixedWindowCounter(window_size=60.0, limit=10)

    await limiter.acquire("docker_user")
    await limiter.acquire("docker_user_2")

    await limiter.reset("docker_user")

    key = get_current_window_key("docker_user", 60.0)
    key_exists = await test_redis_client.exists(key)
    assert key_exists == 0

    # Other keys should still exist
    key_2 = get_current_window_key("docker_user_2", 60.0)
    key_exists_2 = await test_redis_client.exists(key_2)
    assert key_exists_2 == 1