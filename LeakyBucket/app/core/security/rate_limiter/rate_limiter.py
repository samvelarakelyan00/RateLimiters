# Standard libs
import time
from typing import Final, Any

# Own Modules
from core.security.rate_limiter.redis_manager import redis_manager


# Optimized Leaky Bucket Lua script using standard Redis Strings instead of Hashes.
# Reduces CPU usage and memory footprint, executing over a single network operation.
LEAKY_BUCKET_LUA: Final[str] = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local leak_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

-- Retrieve current state from the Redis String
local raw_data = redis.call('GET', key)
local water_level
local last_update

if raw_data then
    -- Decode string data structured as "water_level:last_update"
    local split_idx = string.find(raw_data, ":")
    water_level = tonumber(string.sub(raw_data, 1, split_idx - 1))
    last_update = tonumber(string.sub(raw_data, split_idx + 1))
else
    -- Initialize if the key does not exist yet (empty bucket)
    water_level = 0.0
    last_update = now
end

-- Calculate how much water has leaked since the last request
local elapsed = now - last_update
local leaked = elapsed * leak_rate
water_level = math.max(0.0, water_level - leaked)

-- Check if the incoming request fits into the bucket capacity
if water_level + requested <= capacity then
    water_level = water_level + requested
    local payload = tostring(water_level) .. ":" .. tostring(now)
    redis.call('SET', key, payload, 'EX', 3600)
    return 1 -- Access ALLOWED
else
    -- Update state even on rejection to maintain correct lazy evaluation state
    local payload = tostring(water_level) .. ":" .. tostring(now)
    redis.call('SET', key, payload, 'EX', 3600)
    return 0 -- Access DENIED
end
"""


class LeakyBucket:
    """
    A high-performance, distributed Leaky Bucket rate limiter utilizing Redis and Lua.

    Optimized for high-concurrency environments by implementing EVALSHA script caching
    and lightweight Redis String primitives to minimize atomic execution bottlenecks.
    """

    def __init__(self, capacity: float, leak_rate: float):
        """
        Initialize the rate limiter configuration and register the Lua script.

        :param capacity: Maximum bucket capacity (maximum accumulated burst size).
        :param leak_rate: Sustained leaking rate (tokens/requests processed per second).
        """
        self.capacity = capacity
        self.leak_rate = leak_rate

        # Pre-loads the Lua script into Redis memory via 'SCRIPT LOAD'.
        # Subsequent invocations transparently use 'EVALSHA' using the 40-character SHA1 hash.
        self._lua_executable: Any = redis_manager.client.register_script(LEAKY_BUCKET_LUA)

    async def acquire(self, search_key: str, tokens: float = 1.0) -> bool:
        """
        Attempt to add tokens (water) into the bucket for a given key.

        :param search_key: Unique identifier for the rate-limiting scope (compatible with Redis Cluster).
        :param tokens: Token cost of the incoming request (amount of water to add).
        :return: True if the request is within limits (allowed), False if rate-limited (denied).
        """
        # Global synchronized Unix epoch timestamp (NTP-resilient)
        time_now = time.time()

        # Execute script implicitly via EVALSHA for high performance
        result = await self._lua_executable(
            keys=[search_key],
            args=[self.capacity, self.leak_rate, time_now, tokens]
        )

        return bool(result)
