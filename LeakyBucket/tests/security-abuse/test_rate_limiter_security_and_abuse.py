import asyncio
import pytest
from httpx import AsyncClient

from core.security.rate_limiter.rate_limiter import LeakyBucket
from core.security.rate_limiter.rate_limit_service import RateLimitService

URL_COMMON_PART = "/api/v1/auth"


# --------------------------------------------------------------------------------------
# Reverse Proxy Spoofing & Header Interception Checks
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_x_forwarded_for_spoofing_isolation(async_http_client: AsyncClient, test_redis_client,
                                                  monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    email = "spoof_check@test.com"
    payload = {"email": email, "password": "password"}

    await async_http_client.post(
        f"{URL_COMMON_PART}/login",
        json=payload,
        headers={"X-Forwarded-For": "203.0.113.195, 70.41.3.18, 150.172.238.178"}
    )

    stored_user_ip = await test_redis_client.keys("rate:login:ip:203.0.113.195")
    stored_proxy_ip = await test_redis_client.keys("rate:login:ip:70.41.3.18")

    assert len(stored_user_ip) == 1
    assert len(stored_proxy_ip) == 0


@pytest.mark.asyncio
async def test_cloudflare_connecting_ip_precedence(async_http_client: AsyncClient, test_redis_client,
                                                   monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    email = "cf_check@test.com"
    payload = {"email": email, "password": "password"}

    await async_http_client.post(
        f"{URL_COMMON_PART}/login",
        json=payload,
        headers={"CF-Connecting-IP": "198.51.100.42"}
    )

    stored_cf_ip = await test_redis_client.keys("rate:login:ip:198.51.100.42")
    assert len(stored_cf_ip) == 1


# --------------------------------------------------------------------------------------
# Injection Attack Mitigation
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_key_injection_attack_safety(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=1.0)

    malicious_key = "user\r\nSET overflowed 1\r\n"

    result = await limiter.acquire(malicious_key)
    assert result is True

    arbitrary_key_exists = await test_redis_client.exists("overflowed")
    assert arbitrary_key_exists == 0


# --------------------------------------------------------------------------------------
# Distributed High-Velocity Exploitation (DDoS Sim)
# --------------------------------------------------------------------------------------
@pytest.mark.xfail(reason="Event loop issue with multiple requests")
@pytest.mark.asyncio
async def test_distributed_attack_on_single_account(async_http_client: AsyncClient, test_redis_client,
                                                    monkeypatch) -> None:
    # Create a fresh Redis client for this test
    import redis.asyncio as aioredis

    fresh_client = aioredis.Redis(
        host="redis",
        port=6379,
        decode_responses=True,
        max_connections=10,
        socket_timeout=5,
        socket_connect_timeout=5,
    )

    try:
        await fresh_client.flushdb()
        monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", fresh_client)

        target_email = "victim@test.com"
        payload = {"email": target_email, "password": "password"}

        status_codes = []
        for i in range(10):
            response = await async_http_client.post(
                f"{URL_COMMON_PART}/login",
                json=payload,
                headers={"X-Forwarded-For": f"192.168.1.{i}"}
            )
            status_codes.append(response.status_code)
            await asyncio.sleep(0.01)

        assert status_codes.count(200) == 3
        assert status_codes.count(429) == 7
    finally:
        await fresh_client.aclose(close_connection_pool=True)


# --------------------------------------------------------------------------------------
# Multi-Namespace Scope Isolation
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_endpoint_namespace_and_key_isolation(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = LeakyBucket(capacity=1.0, leak_rate=0.0)

    login_key = RateLimitService.build_email_key("login", "attacker@test.com")
    signup_key = RateLimitService.build_email_key("signup", "attacker@test.com")

    login_res1 = await limiter.acquire(login_key)
    login_res2 = await limiter.acquire(login_key)
    signup_res1 = await limiter.acquire(signup_key)

    assert login_res1 is True
    assert login_res2 is False
    assert signup_res1 is True