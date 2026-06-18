# Own Modules
from core.security.rate_limiter.redis_client import (
    redis_client
)


async def verify_redis_connection() -> None:
    await redis_client.ping()