# Standard libs
import asyncio

# Non-Standard libs
import pytest

# Own Modules
from core.security.rate_limiter.rate_limiter import LeakyBucket


# --------------------------------------------------------------------------------------
# Basic Request Flow
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_first_request_is_allowed_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=3.0, leak_rate=1.0)

    result = await limiter.acquire("docker_user_1")
    assert result is True
    stored_user = await test_redis_client.hgetall("docker_user_1")
    assert stored_user is not None and float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)


@pytest.mark.asyncio
async def test_second_request_is_allowed_before_capacity_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=3.0, leak_rate=1.0)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert stored_user is not None and float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)

    second_result = await limiter.acquire("docker_user")
    assert second_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert stored_user is not None and float(stored_user["water_level"]) == pytest.approx(2.0, abs=1e-2)


@pytest.mark.asyncio
async def test_fourth_request_exceeds_capacity_and_is_denied_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=3.0, leak_rate=1.0)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert stored_user is not None and float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)

    second_result = await limiter.acquire("docker_user")
    assert second_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert stored_user is not None and float(stored_user["water_level"]) == pytest.approx(2.0, abs=1e-2)

    third_result = await limiter.acquire("docker_user")
    assert third_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert stored_user is not None and float(stored_user["water_level"]) == pytest.approx(3.0, abs=1e-2)

    fourth_result = await limiter.acquire("docker_user")
    assert fourth_result is False
    stored_user = await test_redis_client.hgetall("docker_user")
    assert stored_user is not None and float(stored_user["water_level"]) == pytest.approx(3.0, abs=1e-2)


@pytest.mark.asyncio
async def test_request_above_capacity_is_blocked_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=3.0, leak_rate=1.0)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)

    second_result = await limiter.acquire("docker_user")
    assert second_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(2.0, abs=1e-2)

    third_result = await limiter.acquire("docker_user")
    assert third_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(3.0, abs=1e-2)

    fourth_result = await limiter.acquire("docker_user")
    assert fourth_result is False
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(3.0, abs=1e-2)

    fifth_result = await limiter.acquire("docker_user")
    assert fifth_result is False
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(3.0, abs=1e-2)


@pytest.mark.asyncio
async def test_multiple_requests_after_block_remain_blocked_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=1.0)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)

    second_result = await limiter.acquire("docker_user")
    assert second_result is False
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)

    third_result = await limiter.acquire("docker_user")
    assert third_result is False
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)

    fourth_result = await limiter.acquire("docker_user")
    assert fourth_result is False
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)


# --------------------------------------------------------------------------------------
# Key Isolation
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_different_keys_are_independent_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=1.0)

    first_result = await limiter.acquire("docker_user_1")
    assert first_result is True
    stored_user_1 = await test_redis_client.hgetall("docker_user_1")
    assert float(stored_user_1["water_level"]) == pytest.approx(1.0, abs=1e-2)

    second_result = await limiter.acquire("docker_user_2")
    assert second_result is True
    stored_user_2 = await test_redis_client.hgetall("docker_user_2")
    assert float(stored_user_2["water_level"]) == pytest.approx(1.0, abs=1e-2)


@pytest.mark.asyncio
async def test_same_key_uses_same_bucket_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=1.0)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)

    second_result = await limiter.acquire("docker_user")
    assert second_result is False
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)


@pytest.mark.asyncio
async def test_many_keys_do_not_interfere_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=1.0)

    for i in range(100):
        key = f"docker_user_{i}"
        result = await limiter.acquire(key)
        assert result is True

        stored_user = await test_redis_client.hgetall(key)
        assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)


# --------------------------------------------------------------------------------------
# Leak Recovery
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_bucket_recovers_after_leak_period_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=1.0)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)

    await asyncio.sleep(1.1)

    second_result = await limiter.acquire("docker_user")
    assert second_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)


@pytest.mark.asyncio
async def test_partial_leak_does_not_fully_reset_bucket_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=2.0, leak_rate=1.0)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)

    second_result = await limiter.acquire("docker_user")
    assert second_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(2.0, abs=1e-2)

    third_result = await limiter.acquire("docker_user")
    assert third_result is False
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(2.0, abs=1e-2)

    await asyncio.sleep(1.1)

    fourth_result = await limiter.acquire("docker_user")
    assert fourth_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.9, abs=1e-1)

    fifth_result = await limiter.acquire("docker_user")
    assert fifth_result is False
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.9, abs=1e-1)


@pytest.mark.asyncio
async def test_full_leak_empties_bucket_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=2.0, leak_rate=2.0)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)

    second_result = await limiter.acquire("docker_user")
    assert second_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(2.0, abs=1e-2)

    third_result = await limiter.acquire("docker_user")
    assert third_result is False
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(2.0, abs=1e-1)

    await asyncio.sleep(2.1)

    fourth_result = await limiter.acquire("docker_user")
    assert fourth_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-1)


@pytest.mark.asyncio
async def test_high_leak_rate_recovers_faster_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=10.0)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)

    await asyncio.sleep(0.11)

    second_result = await limiter.acquire("docker_user")
    assert second_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-1)


@pytest.mark.asyncio
async def test_low_leak_rate_recovers_slower_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=0.1)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)

    await asyncio.sleep(0.5)

    second_result = await limiter.acquire("docker_user")
    assert second_result is False
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(0.95, abs=1e-2)


# --------------------------------------------------------------------------------------
# Capacity Edge Cases
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_capacity_one_allows_single_request_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=1.0)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)


@pytest.mark.asyncio
async def test_capacity_one_blocks_second_request_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=1.0)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1.0, abs=1e-2)

    second_result = await limiter.acquire("docker_user")
    assert second_result is False
    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(0.99, abs=1e-2)


@pytest.mark.asyncio
async def test_large_capacity_allows_many_requests_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1000.0, leak_rate=0.0)

    for _ in range(1000):
        result = await limiter.acquire("docker_user")
        assert result is True

    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1000.0, abs=1e-2)


@pytest.mark.asyncio
async def test_large_capacity_blocks_after_limit_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1000.0, leak_rate=0.0)

    for _ in range(1000):
        await limiter.acquire("docker_user")

    result = await limiter.acquire("docker_user")
    assert result is False

    stored_user = await test_redis_client.hgetall("docker_user")
    assert float(stored_user["water_level"]) == pytest.approx(1000.0, abs=1e-2)


# --------------------------------------------------------------------------------------
# Redis State Validation
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_bucket_created_after_first_request_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=1.0)

    result = await limiter.acquire("docker_user")
    assert result is True

    key_exists = await test_redis_client.exists("docker_user")
    assert key_exists == 1


@pytest.mark.asyncio
async def test_bucket_stores_water_level_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=3.0, leak_rate=1.0)

    result = await limiter.acquire("docker_user")
    assert result is True

    bucket = await test_redis_client.hgetall("docker_user")
    assert float(bucket["water_level"]) > 0


@pytest.mark.asyncio
async def test_water_level_never_negative_integration(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=1000.0)

    first_result = await limiter.acquire("docker_user")
    assert first_result is True

    await asyncio.sleep(0.1)

    second_result = await limiter.acquire("docker_user")
    assert second_result is True

    bucket = await test_redis_client.hgetall("docker_user")
    assert float(bucket["water_level"]) >= 0
