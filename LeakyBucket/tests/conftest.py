# Standard libs
from typing import Generator, AsyncGenerator
from httpx import AsyncClient, ASGITransport

# Non-Standard libs
import pytest
import redis.asyncio as aioredis
from testcontainers.redis import RedisContainer


@pytest.fixture(scope="session")
def redis_container() -> Generator[RedisContainer, None, None]:
    """
    Spins up an isolated Redis Docker container automatically before any tests run.
    Cleans up and destroys the container after the entire test session finishes.
    """
    container = RedisContainer("redis:7-alpine")
    with container:
        yield container


@pytest.fixture(scope="function")
async def test_redis_client(redis_container, monkeypatch) -> AsyncGenerator[aioredis.Redis, None]:
    """
    Creates a real async connection client to the automated Docker container.
    Flushes the database before and after each test to ensure complete isolation.
    """
    host = redis_container.get_container_host_ip()
    port = redis_container.get_exposed_port(redis_container.port)

    client = aioredis.Redis(host=host, port=int(port), decode_responses=True, max_connections=50000)

    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", client)

    await client.flushdb()

    yield client

    await client.flushdb()
    await client.aclose(close_connection_pool=True)


@pytest.fixture(scope="function")
async def async_http_client(test_redis_client) -> AsyncGenerator[AsyncClient, None]:
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client
