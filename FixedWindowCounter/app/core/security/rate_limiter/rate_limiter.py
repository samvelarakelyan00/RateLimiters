# Standard libs
import time
from typing import Final, Any

# Own Modules
from core.security.rate_limiter.redis_manager import redis_manager


# Window boundaries are determined by the current timestamp divided by window size.
FIXED_WINDOW_LUA: Final[str] = """
local key = KEYS[1]
local window_size = tonumber(ARGV[1])  -- Window size in seconds
local limit = tonumber(ARGV[2])        -- Maximum requests per window
local now = tonumber(ARGV[3])          -- Current timestamp
local requested = tonumber(ARGV[4])    -- Number of requests to count

local window_key = key .. ":" .. math.floor(now / window_size)
local current_count = redis.call('GET', window_key)

if current_count then
    current_count = tonumber(current_count)
else
    current_count = 0
end

if current_count + requested <= limit then
    local new_count = redis.call('INCRBY', window_key, requested)
    redis.call('EXPIRE', window_key, window_size + 1)

    return 1  -- Access ALLOWED
else
    if current_count == 0 then
        redis.call('SET', window_key, 0, 'EX', window_size + 1)
    end

    return 0  -- Access DENIED
end
"""


class FixedWindowCounter:
    """
    A high-performance, distributed Fixed Window Counter rate limiter utilizing Redis and Lua.

    The Fixed Window Counter algorithm divides time into fixed-size windows (e.g., 60 seconds).
    Each window has a maximum number of allowed requests. When the window passes, the counter resets.

    Key characteristics:
    - Simple and memory efficient (O(1) storage per key)
    - Predictable rate limiting with clear boundaries
    - Potential for burst at window boundaries (double the limit)
    - Optimal for scenarios where periodic resets are acceptable

    Optimized for high-concurrency environments by implementing EVALSHA script caching
    and lightweight Redis String primitives to minimize atomic execution bottlenecks.
    """

    def __init__(self, window_size: float, limit: int):
        self.window_size = window_size
        self.limit = limit
        self._lua_executable: Any = redis_manager.client.register_script(FIXED_WINDOW_LUA)

    async def acquire(self, search_key: str, tokens: int = 1) -> bool:
        """
        Attempt to increment the counter for a given key within the current window.

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
        Get the current count for the active window.

        :param search_key: Unique identifier for the rate-limiting scope.
        :return: Current count in the active window.
        """
        time_now = time.time()
        window_key = f"{search_key}:{int(time_now // self.window_size)}"
        count = await redis_manager.client.get(window_key)

        return int(count) if count else 0

    async def get_remaining(self, search_key: str) -> int:
        """
        Get the remaining capacity in the current window.

        :param search_key: Unique identifier for the rate-limiting scope.
        :return: Remaining requests allowed in the current window.
        """
        current_count = await self.get_current_count(search_key)
        return max(0, self.limit - current_count)

    async def reset_window(self, search_key: str) -> None:
        """
        Reset the current window counter.

        :param search_key: Unique identifier for the rate-limiting scope.
        """
        time_now = time.time()
        window_key = f"{search_key}:{int(time_now // self.window_size)}"
        await redis_manager.client.delete(window_key)

    async def is_window_expired(self, search_key: str) -> bool:
        """
        Check if the current window has expired.

        :param search_key: Unique identifier for the rate-limiting scope.
        :return: True if the window has expired, False otherwise.
        """
        time_now = time.time()
        window_key = f"{search_key}:{int(time_now // self.window_size)}"
        ttl = await redis_manager.client.ttl(window_key)
        return ttl == -2  # -2 means key doesn't exist