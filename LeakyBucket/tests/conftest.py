import pytest_asyncio

from core.security.rate_limiter.redis_client import redis_client


@pytest_asyncio.fixture(autouse=True)
async def clean_redis():
    await redis_client.flushdb()

    yield

    await redis_client.flushdb()