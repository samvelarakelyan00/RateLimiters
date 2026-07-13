# Standard libs
from unittest.mock import AsyncMock, patch

# Non-Standard libs
import pytest

# Own Modules
from core.security.rate_limiter.rate_limiter import FixedWindowCounter


# --------------------------------------------------------------------------------------
# Basic Request Flow
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_first_request_is_allowed(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.return_value = 1
    mock_redis.client.register_script.return_value = mock_script

    limiter = FixedWindowCounter(window_size=60.0, limit=3)

    result = await limiter.acquire("user")

    assert result is True
    mock_redis.client.register_script.assert_called_once()


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_second_request_is_allowed_before_limit(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 1]
    mock_redis.client.register_script.return_value = mock_script

    limiter = FixedWindowCounter(window_size=60.0, limit=3)

    first_result = await limiter.acquire("user")
    second_result = await limiter.acquire("user")

    assert first_result is True
    assert second_result is True
    assert mock_script.call_count == 2


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_fourth_request_exceeds_limit_and_is_denied(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 1, 1, 0]
    mock_redis.client.register_script.return_value = mock_script

    limiter = FixedWindowCounter(window_size=60.0, limit=3)

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
async def test_request_above_limit_is_blocked(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 1, 1, 0]
    mock_redis.client.register_script.return_value = mock_script

    limiter = FixedWindowCounter(window_size=60.0, limit=3)

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

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

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

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

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

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

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

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    for i in range(100):
        result = await limiter.acquire(f"user_{i}")
        assert result is True

    assert mock_script.call_count == 100


# --------------------------------------------------------------------------------------
# Window Recovery (Fixed Window specific)
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_new_window_allows_requests_after_reset(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 0, 1]
    mock_redis.client.register_script.return_value = mock_script

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    first_result = await limiter.acquire("user")
    second_result = await limiter.acquire("user")
    third_result = await limiter.acquire("user")

    assert first_result is True
    assert second_result is False
    assert third_result is True
    assert mock_script.call_count == 3


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_different_window_sizes_work_correctly(mock_redis) -> None:
    mock_script = AsyncMock()
    # With limit=2, first two requests allowed, third and fourth denied
    mock_script.side_effect = [1, 1, 0, 0]
    mock_redis.client.register_script.return_value = mock_script

    limiter = FixedWindowCounter(window_size=10.0, limit=2)

    res1 = await limiter.acquire("user")
    res2 = await limiter.acquire("user")
    res3 = await limiter.acquire("user")
    res4 = await limiter.acquire("user")

    assert res1 is True
    assert res2 is True
    assert res3 is False
    assert res4 is False
    assert mock_script.call_count == 4

# --------------------------------------------------------------------------------------
# Capacity Edge Cases
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_limit_one_allows_single_request(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.return_value = 1
    mock_redis.client.register_script.return_value = mock_script

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    result = await limiter.acquire("user")

    assert result is True
    mock_script.assert_called_once()


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_limit_one_blocks_second_request(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1, 0]
    mock_redis.client.register_script.return_value = mock_script

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    first_result = await limiter.acquire("user")
    second_result = await limiter.acquire("user")

    assert first_result is True
    assert second_result is False
    assert mock_script.call_count == 2


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_large_limit_allows_many_requests(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1 for _ in range(1000)]
    mock_redis.client.register_script.return_value = mock_script

    limiter = FixedWindowCounter(window_size=60.0, limit=1000)

    for _ in range(1000):
        result = await limiter.acquire("user")
        assert result is True

    assert mock_script.call_count == 1000


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_large_limit_blocks_after_limit(mock_redis) -> None:
    mock_script = AsyncMock()
    mock_script.side_effect = [1 for _ in range(1000)] + [0]
    mock_redis.client.register_script.return_value = mock_script

    limiter = FixedWindowCounter(window_size=60.0, limit=1000)

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

    limiter = FixedWindowCounter(window_size=60.0, limit=1)

    result = await limiter.acquire("user")

    assert result is True
    mock_script.assert_called_once()


# --------------------------------------------------------------------------------------
# Utility Methods
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_get_current_count_returns_zero_for_new_key(mock_redis) -> None:
    mock_redis.client.get = AsyncMock(return_value=None)

    limiter = FixedWindowCounter(window_size=60.0, limit=10)

    count = await limiter.get_current_count("user")

    assert count == 0
    mock_redis.client.get.assert_called_once()


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_get_current_count_returns_existing_count(mock_redis) -> None:
    mock_redis.client.get = AsyncMock(return_value="5")

    limiter = FixedWindowCounter(window_size=60.0, limit=10)

    count = await limiter.get_current_count("user")

    assert count == 5
    mock_redis.client.get.assert_called_once()


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_get_remaining_returns_correct_value(mock_redis) -> None:
    mock_redis.client.get = AsyncMock(return_value="3")

    limiter = FixedWindowCounter(window_size=60.0, limit=10)

    remaining = await limiter.get_remaining("user")

    assert remaining == 7


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_get_remaining_returns_limit_for_new_key(mock_redis) -> None:
    mock_redis.client.get = AsyncMock(return_value=None)

    limiter = FixedWindowCounter(window_size=60.0, limit=10)

    remaining = await limiter.get_remaining("user")

    assert remaining == 10


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_get_remaining_never_negative(mock_redis) -> None:
    mock_redis.client.get = AsyncMock(return_value="15")

    limiter = FixedWindowCounter(window_size=60.0, limit=10)

    remaining = await limiter.get_remaining("user")

    assert remaining == 0


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_reset_deletes_all_keys_for_search_key(mock_redis) -> None:
    mock_redis.client.keys = AsyncMock(return_value=["user:123", "user:456"])
    mock_redis.client.delete = AsyncMock(return_value=2)

    limiter = FixedWindowCounter(window_size=60.0, limit=10)

    await limiter.reset("user")

    mock_redis.client.keys.assert_called_once_with("user:*")
    mock_redis.client.delete.assert_called_once_with("user:123", "user:456")


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_reset_handles_no_keys(mock_redis) -> None:
    mock_redis.client.keys = AsyncMock(return_value=[])

    limiter = FixedWindowCounter(window_size=60.0, limit=10)

    await limiter.reset("user")

    mock_redis.client.keys.assert_called_once_with("user:*")
    mock_redis.client.delete.assert_not_called()


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_reset_window_deletes_current_window(mock_redis) -> None:
    mock_redis.client.delete = AsyncMock()
    mock_redis.client.get = AsyncMock(return_value=None)

    limiter = FixedWindowCounter(window_size=60.0, limit=10)

    await limiter.reset_window("user")

    mock_redis.client.delete.assert_called_once()


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_is_window_expired_returns_true_for_missing_key(mock_redis) -> None:
    mock_redis.client.ttl = AsyncMock(return_value=-2)

    limiter = FixedWindowCounter(window_size=60.0, limit=10)

    result = await limiter.is_window_expired("user")

    assert result is True
    mock_redis.client.ttl.assert_called_once()


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_is_window_expired_returns_false_for_existing_key(mock_redis) -> None:
    mock_redis.client.ttl = AsyncMock(return_value=30)

    limiter = FixedWindowCounter(window_size=60.0, limit=10)

    result = await limiter.is_window_expired("user")

    assert result is False
    mock_redis.client.ttl.assert_called_once()


@pytest.mark.asyncio
@patch("core.security.rate_limiter.rate_limiter.redis_manager", autospec=True)
async def test_is_window_expired_returns_false_for_no_expiry(mock_redis) -> None:
    mock_redis.client.ttl = AsyncMock(return_value=-1)

    limiter = FixedWindowCounter(window_size=60.0, limit=10)

    result = await limiter.is_window_expired("user")

    assert result is False
    mock_redis.client.ttl.assert_called_once()