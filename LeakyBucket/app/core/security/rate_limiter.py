# Standard libs
import asyncio
import time
from typing import Dict, Tuple


class LeakyBucketLimiter:
    def __init__(self, capacity: int, leak_rate: float) -> None:
        self.capacity = capacity
        self.leak_rate = leak_rate
        self._buckets: Dict[str, Tuple[float, float]] = {}
        self._lock = asyncio.Lock()

    async def acquire(self, key: str) -> bool:
        async with self._lock:
            now = time.monotonic()
            water_level, last_update = self._buckets.get(key, (0.0, now))

            leaked = (now - last_update) * self.leak_rate
            water_level = max(0.0, water_level - leaked)

            if water_level + 1 <= self.capacity:
                self._buckets[key] = (water_level + 1, now)
                return False

            if water_level == 0.0:
                self._buckets[key] = (0.0, now)
            else:
                self._buckets[key] = (water_level, last_update)

            return True
