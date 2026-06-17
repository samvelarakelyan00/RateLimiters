# Standard libs
import time
from typing import Dict, Tuple


class LeakyBucketLimiter:
    def __init__(self, capacity: int, leak_rate: float, cleanup_interval: int = 60) -> None:
        self.capacity = capacity
        self.leak_rate = leak_rate
        self._cleanup_interval = cleanup_interval

        self._buckets: Dict[str, Tuple[float, float]] = {}
        self._last_cleanup = time.monotonic()

    async def acquire(self, key: str) -> bool:
        """
        Evaluates the rate limit for a specific key.
        Returns True if the request is rate-limited (blocked), False if allowed.
        """
        now = time.monotonic()

        if now - self._last_cleanup > self._cleanup_interval:
            self._evict_expired_buckets(now)

        water_level, last_update = self._buckets.get(key, (0.0, now))

        leaked = (now - last_update) * self.leak_rate
        water_level = max(0.0, water_level - leaked)

        if water_level + 1 <= self.capacity:
            self._buckets[key] = (water_level + 1, now)
            return False  # Request Allowed

        self._buckets[key] = (water_level, now)
        return True  # Request Blocked

    def _evict_expired_buckets(self, now: float) -> None:
        """Removes dry buckets completely from RAM memory to prevent OOM errors."""
        expired_keys = [
            key for key, (water, last_upd) in self._buckets.items()
            if water - ((now - last_upd) * self.leak_rate) <= 0
        ]
        for key in expired_keys:
            self._buckets.pop(key, None)
        self._last_cleanup = now
