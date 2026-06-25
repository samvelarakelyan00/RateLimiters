import time
from typing import Final

from core.security.rate_limiter.redis_manager import redis_manager


# Atomic Lua script to eliminate Race Conditions in distributed environments.
# Redis executes Lua scripts sequentially, guaranteeing thread and process safety.
TOKEN_BUCKET_LUA: Final[str] = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

-- Retrieve current state from the Redis Hash
local bucket = redis.call('HMGET', key, 'tokens', 'last_update')
local tokens = tonumber(bucket[1])
local last_update = tonumber(bucket[2]) or now

-- Initialize bucket state if it does not exist
if not tokens then
    tokens = capacity
    last_update = now
else
    -- Calculate how many tokens have replenished since the last request
    local elapsed = now - last_update
    local refilled = elapsed * refill_rate
    tokens = math.min(capacity, tokens + refilled)
end

-- Check if the incoming request fits into the available tokens
if tokens >= requested then
    tokens = tokens - requested
    redis.call('HSET', key, 'tokens', tokens, 'last_update', now)
    redis.call('EXPIRE', key, 3600)
    return 1 -- Access ALLOWED
else
    -- Update state even on rejection to maintain correct lazy evaluation state
    redis.call('HSET', key, 'tokens', tokens, 'last_update', now)
    redis.call('EXPIRE', key, 3600)
    return 0 -- Access DENIED
end
"""


class TokenBucket:
    """
    A distributed, thread-safe Token Bucket rate limiter utilizing Redis and Lua.

    This class ensures atomic operations across multi-process or multi-server
    environments, eliminating race conditions and synchronizing time via epoch timestamps.
    """

    def __init__(self, capacity: float, refill_rate: float):
        """
        Initialize the rate limiter configuration.

        :param capacity: Maximum burst size (total tokens allowed simultaneously).
        :param refill_rate: Sustained processing rate (tokens replenished per second).
        """
        self.capacity = capacity
        self.refill_rate = refill_rate

    async def acquire(self, search_key: str, tokens: float = 1.0) -> bool:
        """
        Attempt to consume tokens from the bucket for a given key.

        :param search_key: Unique identifier for the rate-limiting scope (e.g., "rate_limit:ip:127.0.0.1").
        :param tokens: Token cost of the request (default: 1.0).
        :return: True if the request is within limits (allowed), False if rate-limited (denied).
        """
        # time.time() is synchronized across servers via NTP, unlike time.monotonic()
        time_now = time.time()

        # Execute the Lua script atomically on the Redis server
        result = await redis_manager.client.eval(
            TOKEN_BUCKET_LUA,
            1,  # Number of keys passed to the script
            search_key,
            self.capacity,
            self.refill_rate,
            time_now,
            tokens
        )

        # Converts Redis response (1 or 0) into Python boolean (True or False)
        return bool(result)
