# Standard libs
import time
from typing import Final, Any

# Own Modules
from core.security.rate_limiter.redis_manager import redis_manager

# Sliding Window Counter Lua script using Redis Strings for counters.
# Combines fixed window counter with weighted average for accurate sliding window behavior.
SLIDING_WINDOW_COUNTER_LUA: Final[str] = """
local key = KEYS[1]
local window_size = tonumber(ARGV[1])  -- Window size in seconds
local limit = tonumber(ARGV[2])        -- Maximum requests per window
local now = tonumber(ARGV[3])          -- Current timestamp
local requested = tonumber(ARGV[4])    -- Number of requests to count

-- Calculate current window
local current_window = math.floor(now / window_size)
local previous_window = current_window - 1
local current_window_key = key .. ":" .. current_window
local previous_window_key = key .. ":" .. previous_window

-- Get counts for both windows
local current_count = redis.call('GET', current_window_key) or 0
local previous_count = redis.call('GET', previous_window_key) or 0

-- Calculate weighted average
local elapsed_in_window = now - (current_window * window_size)
local weight = elapsed_in_window / window_size
local estimated_count = (previous_count * (1 - weight)) + (current_count * weight)

-- Check if the request would exceed the limit
if estimated_count + requested <= limit then
    -- Increment the current window counter
    local new_count = redis.call('INCRBY', current_window_key, requested)
    redis.call('EXPIRE', current_window_key, window_size * 2)

    return 1  -- Access ALLOWED
else
    -- Ensure key exists with proper expiry
    redis.call('EXPIRE', current_window_key, window_size * 2)
    return 0  -- Access DENIED
end
"""


class SlidingWindowCounter:
    """
    A high-performance, distributed Sliding Window Counter rate limiter utilizing Redis and Lua.

    The Sliding Window Counter algorithm combines the efficiency of fixed windows
    with the accuracy of sliding windows using a weighted average approach.

    Key characteristics:
    - Good balance of accuracy and memory efficiency
    - O(1) storage per key (unlike Sliding Window Log)
    - No burst at window boundaries
    - Approximate but accurate for most use cases
    - Lower memory usage than Sliding Window Log

    Optimized for high-concurrency environments by implementing EVALSHA script caching
    and lightweight Redis String primitives to minimize atomic execution bottlenecks.
    """

    def __init__(self, window_size: float, limit: int):
        """
        Initialize the rate limiter configuration and register the Lua script.

        :param window_size: Size of the sliding window in seconds.
        :param limit: Maximum number of requests allowed in the window.
        """
        self.window_size = window_size
        self.limit = limit

        # Pre-loads the Lua script into Redis memory via 'SCRIPT LOAD'.
        # Subsequent invocations transparently use 'EVALSHA' using the 40-character SHA1 hash.
        self._lua_executable: Any = redis_manager.client.register_script(SLIDING_WINDOW_COUNTER_LUA)

    async def acquire(self, search_key: str, tokens: int = 1) -> bool:
        """
        Attempt to increment the counter for a given key within the sliding window.

        :param search_key: Unique identifier for the rate-limiting scope.
        :param tokens: Number of tokens/requests to consume (default: 1).
        :return: True if the request is within limits, False if rate-limited.
        """
        time_now = time.time()

        result = await self._lua_executable(
            keys=[search_key],
            args=[self.window_size, self.limit, time_now, tokens]
        )

        return bool(result)

    async def reset(self, search_key: str) -> None:
        """
        Manually reset the counter for a given key.
        Useful for testing or administrative purposes.

        :param search_key: Unique identifier for the rate-limiting scope.
        """
        pattern = f"{search_key}:*"
        keys = await redis_manager.client.keys(pattern)
        if keys:
            await redis_manager.client.delete(*keys)

    async def get_current_count(self, search_key: str) -> int:
        """
        Get the current count in the sliding window.

        :param search_key: Unique identifier for the rate-limiting scope.
        :return: Current count in the sliding window.
        """
        time_now = time.time()
        current_window = int(time_now // self.window_size)
        previous_window = current_window - 1
        current_window_key = f"{search_key}:{current_window}"
        previous_window_key = f"{search_key}:{previous_window}"

        current_count = await redis_manager.client.get(current_window_key)
        previous_count = await redis_manager.client.get(previous_window_key)

        # Convert to int, default to 0 if None
        current_count = int(current_count) if current_count else 0
        previous_count = int(previous_count) if previous_count else 0

        elapsed_in_window = time_now - (current_window * self.window_size)
        weight = elapsed_in_window / self.window_size

        return int((previous_count * (1 - weight)) + (current_count * weight))

    async def get_remaining(self, search_key: str) -> int:
        """
        Get the remaining capacity in the sliding window.

        :param search_key: Unique identifier for the rate-limiting scope.
        :return: Remaining requests allowed in the sliding window.
        """
        current_count = await self.get_current_count(search_key)
        return max(0, self.limit - current_count)

    async def get_current_window_count(self, search_key: str) -> int:
        """
        Get the count for the current fixed window.

        :param search_key: Unique identifier for the rate-limiting scope.
        :return: Count in the current fixed window.
        """
        time_now = time.time()
        current_window = int(time_now // self.window_size)
        current_window_key = f"{search_key}:{current_window}"
        count = await redis_manager.client.get(current_window_key)
        return int(count) if count else 0

    async def get_previous_window_count(self, search_key: str) -> int:
        """
        Get the count for the previous fixed window.

        :param search_key: Unique identifier for the rate-limiting scope.
        :return: Count in the previous fixed window.
        """
        time_now = time.time()
        current_window = int(time_now // self.window_size)
        previous_window = current_window - 1
        previous_window_key = f"{search_key}:{previous_window}"
        count = await redis_manager.client.get(previous_window_key)
        return int(count) if count else 0

    async def get_weight(self, search_key: str) -> float:
        """
        Get the current weight for the sliding window calculation.

        :param search_key: Unique identifier for the rate-limiting scope.
        :return: Weight value between 0 and 1.
        """
        time_now = time.time()
        current_window = int(time_now // self.window_size)
        elapsed_in_window = time_now - (current_window * self.window_size)
        return elapsed_in_window / self.window_size