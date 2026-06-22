import time
from typing import Final

from core.security.rate_limiter.redis_manager import redis_manager


# Atomic Lua script to eliminate Race Conditions in distributed environments.
# Redis executes Lua scripts sequentially, guaranteeing thread and process safety.
LEAKY_BUCKET_LUA: Final[str] = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local leak_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])
local requested = tonumber(ARGV[4])

-- Retrieve current state from the Redis Hash
local bucket = redis.call('HMGET', key, 'water_level', 'last_update')
local water_level = tonumber(bucket[1]) or 0.0
local last_update = tonumber(bucket[2]) or now

-- Calculate how much water has leaked since the last request
local leaked = (now - last_update) * leak_rate
water_level = math.max(0.0, water_level - leaked)

-- Check if the incoming request fits into the bucket capacity
if water_level + requested <= capacity then
    water_level = water_level + requested
    redis.call('HSET', key, 'water_level', water_level, 'last_update', now)
    redis.call('EXPIRE', key, 3600)
    return 1 -- Access ALLOWED
else
    -- Update state even on rejection to maintain correct lazy evaluation state
    redis.call('HSET', key, 'water_level', water_level, 'last_update', now)
    redis.call('EXPIRE', key, 3600)
    return 0 -- Access DENIED
end
"""


class LeakyBucket:
    """
    A distributed, thread-safe Leaky Bucket rate limiter utilizing Redis and Lua.

    This class ensures atomic operations across multi-process or multi-server
    environments, eliminating race conditions and synchronizing time via epoch timestamps.
    """

    def __init__(self, capacity: float, leak_rate: float):
        """
        Initialize the rate limiter configuration.

        :param capacity: Maximum burst size (total tokens allowed simultaneously).
        :param leak_rate: Sustained processing rate (tokens per second).
        """
        self.capacity = capacity
        self.leak_rate = leak_rate

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
            LEAKY_BUCKET_LUA,
            1,  # Number of keys passed to the script
            search_key,
            self.capacity,
            self.leak_rate,
            time_now,
            tokens
        )

        # Converts Redis response (1 or 0) into Python boolean (True or False)
        return bool(result)
