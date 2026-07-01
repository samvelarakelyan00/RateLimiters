import time
from typing import Final, Any
from core.security.rate_limiter.redis_manager import redis_manager


# Optimized Token Bucket Lua script using standard Redis Strings instead of Hashes.
# String operations (GET/SET) have lower CPU overhead than Hash operations (HMGET/HSET).
TOKEN_BUCKET_LUA: Final[str] = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

-- Retrieve current state from the Redis String
local raw_data = redis.call('GET', key)
local tokens
local last_update

if raw_data then
    -- Decode string data structured as "tokens:last_update"
    local split_idx = string.find(raw_data, ":")
    tokens = tonumber(string.sub(raw_data, 1, split_idx - 1))
    last_update = tonumber(string.sub(raw_data, split_idx + 1))
else
    -- Initialize if the key does not exist yet
    tokens = capacity
    last_update = now
end

-- Lazy-evaluate token regeneration based on elapsed time
local elapsed = now - last_update
local refilled = elapsed * refill_rate
tokens = math.min(capacity, tokens + refilled)

-- Evaluate request admissibility and update state
if tokens >= requested then
    tokens = tokens - requested
    local payload = tostring(tokens) .. ":" .. tostring(now)
    redis.call('SET', key, payload, 'EX', 3600)
    return 1 -- Access ALLOWED
else
    local payload = tostring(tokens) .. ":" .. tostring(now)
    redis.call('SET', key, payload, 'EX', 3600)
    return 0 -- Access DENIED
end
"""


class TokenBucket:
    """
    A high-performance, distributed Token Bucket rate limiter utilizing Redis and Lua.

    Optimized for high-concurrency environments by implementing EVALSHA script caching
    and lightweight Redis String primitives to minimize atomic execution bottlenecks.
    """

    def __init__(self, capacity: float, refill_rate: float):
        """
        Initialize the rate limiter configuration and register the Lua script.

        :param capacity: Maximum burst size (total tokens allowed simultaneously).
        :param refill_rate: Sustained processing rate (tokens replenished per second).
        """
        self.capacity = capacity
        self.refill_rate = refill_rate

        # Pre-loads the Lua script into Redis memory via 'SCRIPT LOAD'.
        # Subsequent invocations transparently use 'EVALSHA' using the 40-character SHA1 hash.
        self._lua_executable: Any = redis_manager.client.register_script(TOKEN_BUCKET_LUA)

    async def acquire(self, search_key: str, tokens: float = 1.0) -> bool:
        """
        Attempt to consume tokens from the bucket for a given key.

        :param search_key: Unique identifier for the rate-limiting scope (compatible with Redis Cluster).
        :param tokens: Token cost of the incoming request.
        :return: True if the request is within limits, False if rate-limited.
        """
        # Global synchronized Unix epoch timestamp (NTP-resilient)
        time_now = time.time()

        # Execute script via EVALSHA
        result = await self._lua_executable(
            keys=[search_key],
            args=[self.capacity, self.refill_rate, time_now, tokens]
        )

        return bool(result)
