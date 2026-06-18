# Standard libs
import time

# Own Modules
from core.security.rate_limiter.redis_client import (
    redis_client
)


class LeakyBucketLimiter:
    def __init__(self, capacity: int, leak_rate: float) -> None:
        self.capacity = capacity
        self.leak_rate = leak_rate

    async def acquire(self, key: str) -> bool:
        now = time.monotonic()
        bucket = await redis_client.hgetall(key)

        if not bucket:
            water_level = 0.0
            last_update = now
        else:
            water_level = float(bucket["water_level"])
            last_update = float(bucket["last_update"])

        leaked = (now - last_update) * self.leak_rate
        water_level = max(0.0, water_level - leaked)

        if water_level + 1 <= self.capacity:
            await redis_client.hset(
                key,
                mapping={
                    "water_level": water_level + 1,
                    "last_update": now
                }
            )

            await redis_client.expire(key, 3600)

            return False

        await redis_client.hset(
            key,
            mapping={
                "water_level": water_level,
                "last_update": now
            }
        )

        await redis_client.expire(key, 3600)

        return True