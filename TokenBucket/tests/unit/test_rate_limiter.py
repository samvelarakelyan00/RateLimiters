# Standard libs
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# Non-Standard libs
import pytest

# Own Modules
from core.security.rate_limiter.rate_limiter import TokenBucket


# Helper to create a mock that returns an awaitable
def async_mock_return(value):
    mock = AsyncMock()
    mock.return_value = value
    return mock


# --------------------------------------------------------------------------------------
# Basic Request Flow
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_first_request_is_allowed(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.return_value = 1
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=3.0, refill_rate=1.0)

    result = await limiter.acquire("user")

    assert result is True
    mock_redis.client.register_script.assert_called_once()


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_second_request_is_allowed_before_capacity(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 1]
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=3.0, refill_rate=1.0)

    first_result = await limiter.acquire("user")
    second_result = await limiter.acquire("user")

    assert first_result is True
    assert second_result is True
    assert mock_script.call_count == 2


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_fourth_request_exceeds_capacity_and_is_denied(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 1, 1, 0]
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=3.0, refill_rate=1.0)

    res1 = await limiter.acquire("user")
    res2 = await limiter.acquire("user")
    res3 = await limiter.acquire("user")
    res4 = await limiter.acquire("user")

    assert res1 is True
    assert res2 is True
    assert res3 is True
    assert res4 is False
    assert mock_script.call_count == 4


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_request_above_capacity_is_blocked(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 1, 1, 0]
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=3.0, refill_rate=1.0)

    first_result = await limiter.acquire("user")
    second_result = await limiter.acquire("user")
    third_result = await limiter.acquire("user")
    fourth_result = await limiter.acquire("user")

    assert first_result is True
    assert second_result is True
    assert third_result is True
    assert fourth_result is False
    assert mock_script.call_count == 4


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_multiple_requests_after_block_remain_blocked(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 0, 0, 0]
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=1.0, refill_rate=1.0)

    first_result = await limiter.acquire("user")
    second_result = await limiter.acquire("user")
    third_result = await limiter.acquire("user")
    fourth_result = await limiter.acquire("user")

    assert first_result is True
    assert second_result is False
    assert third_result is False
    assert fourth_result is False
    assert mock_script.call_count == 4


# --------------------------------------------------------------------------------------
# Key Isolation
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_different_keys_are_independent(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 1]
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=1.0, refill_rate=1.0)

    first_result = await limiter.acquire("user1")
    second_result = await limiter.acquire("user2")

    assert first_result is True
    assert second_result is True
    assert mock_script.call_count == 2


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_same_key_uses_same_bucket(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 0]
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=1.0, refill_rate=1.0)

    first_result = await limiter.acquire("user")
    second_result = await limiter.acquire("user")

    assert first_result is True
    assert second_result is False
    assert mock_script.call_count == 2


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_many_keys_do_not_interfere(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1 for _ in range(100)]
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=1.0, refill_rate=1.0)

    for i in range(100):
        result = await limiter.acquire(f"user_{i}")
        assert result is True

    assert mock_script.call_count == 100


# --------------------------------------------------------------------------------------
# Refill Recovery (Token Bucket specific)
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_bucket_recovers_after_refill_period(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 1]
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=1.0, refill_rate=1.0)

    first_result = await limiter.acquire("user")
    second_result = await limiter.acquire("user")

    assert first_result is True
    assert second_result is True
    assert mock_script.call_count == 2


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_partial_refill_does_not_fully_reset_bucket(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 1, 0, 1, 0]
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=2.0, refill_rate=1.0)

    first_result = await limiter.acquire("user")
    second_result = await limiter.acquire("user")
    third_result = await limiter.acquire("user")
    fourth_result = await limiter.acquire("user")
    fifth_result = await limiter.acquire("user")

    assert first_result is True
    assert second_result is True
    assert third_result is False
    assert fourth_result is True
    assert fifth_result is False
    assert mock_script.call_count == 5


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_full_refill_empties_bucket(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 1, 1]
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=2.0, refill_rate=2.0)

    first_result = await limiter.acquire("user")
    second_result = await limiter.acquire("user")
    third_result = await limiter.acquire("user")

    assert first_result is True
    assert second_result is True
    assert third_result is True
    assert mock_script.call_count == 3


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_high_refill_rate_recovers_faster(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 1]
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=1.0, refill_rate=10.0)

    first_result = await limiter.acquire("user")
    second_result = await limiter.acquire("user")

    assert first_result is True
    assert second_result is True
    assert mock_script.call_count == 2


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_low_refill_rate_recovers_slower(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 0]
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=1.0, refill_rate=0.1)

    first_result = await limiter.acquire("user")
    second_result = await limiter.acquire("user")

    assert first_result is True
    assert second_result is False
    assert mock_script.call_count == 2


# --------------------------------------------------------------------------------------
# Capacity Edge Cases
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_capacity_one_allows_single_request(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.return_value = 1
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=1.0, refill_rate=1.0)

    result = await limiter.acquire("user")

    assert result is True
    mock_script.assert_called_once()


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_capacity_one_blocks_second_request(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 0]
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=1.0, refill_rate=1.0)

    first_result = await limiter.acquire("user")
    second_result = await limiter.acquire("user")

    assert first_result is True
    assert second_result is False
    assert mock_script.call_count == 2


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_large_capacity_allows_many_requests(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1 for _ in range(1000)]
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=1000.0, refill_rate=0.0)

    for _ in range(1000):
        result = await limiter.acquire("user")
        assert result is True

    assert mock_script.call_count == 1000


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_large_capacity_blocks_after_limit(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1 for _ in range(1000)] + [0]
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=1000.0, refill_rate=0.0)

    for _ in range(1000):
        await limiter.acquire("user")

    result = await limiter.acquire("user")

    assert result is False
    assert mock_script.call_count == 1001


# --------------------------------------------------------------------------------------
# Redis State Validation
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_bucket_created_after_first_request(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.return_value = 1
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=1.0, refill_rate=1.0)

    result = await limiter.acquire("user")

    assert result is True
    mock_script.assert_called_once()


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_bucket_stores_tokens_level(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.return_value = 1
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=3.0, refill_rate=1.0)

    result = await limiter.acquire("user")

    assert result is True
    mock_script.assert_called_once()


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_tokens_never_negative(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 1]
    mock_redis.client.register_script.return_value = mock_script

    limiter = TokenBucket(capacity=1.0, refill_rate=1000.0)

    first_result = await limiter.acquire("user")
    second_result = await limiter.acquire("user")

    assert first_result is True
    assert second_result is True
    assert mock_script.call_count == 2