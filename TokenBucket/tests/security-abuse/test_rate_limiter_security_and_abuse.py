import asyncio
import pytest
from httpx import AsyncClient

from core.security.rate_limiter.rate_limiter import TokenBucket
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

    response = await async_http_client.post(
        f"{URL_COMMON_PART}/login",
        json=payload,
        headers={"X-Forwarded-For": "203.0.113.195, 70.41.3.18, 150.172.238.178"}
    )

    stored_user_ip = await test_redis_client.keys("rate:login:ip:203.0.113.195")
    stored_proxy_ip = await test_redis_client.keys("rate:login:ip:70.41.3.18")

    assert response.status_code in [200, 429]

    assert len(stored_user_ip) == 1
    assert len(stored_proxy_ip) == 0


@pytest.mark.xfail(reason="Event loop issue with API requests - known issue")
@pytest.mark.asyncio
async def test_cloudflare_connecting_ip_precedence(async_http_client: AsyncClient, test_redis_client,
                                                   monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    email = "cf_check@test.com"
    payload = {"email": email, "password": "password"}

    response = await async_http_client.post(
        f"{URL_COMMON_PART}/login",
        json=payload,
        headers={"CF-Connecting-IP": "198.51.100.42"}
    )

    stored_cf_ip = await test_redis_client.keys("rate:login:ip:198.51.100.42")
    assert len(stored_cf_ip) == 1
    assert response.status_code in [200, 429]


# --------------------------------------------------------------------------------------
# Injection Attack Mitigation
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_key_injection_attack_safety(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=1.0, refill_rate=1.0)

    malicious_key = "user\r\nSET overflowed 1\r\n"

    result = await limiter.acquire(malicious_key)
    assert result is True

    arbitrary_key_exists = await test_redis_client.exists("overflowed")
    assert arbitrary_key_exists == 0


# --------------------------------------------------------------------------------------
# Distributed High-Velocity Exploitation (DDoS Sim)
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_distributed_attack_on_single_account(async_http_client: AsyncClient, test_redis_client,
                                                    monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

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


# --------------------------------------------------------------------------------------
# Multi-Namespace Scope Isolation
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_endpoint_namespace_and_key_isolation(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=1.0, refill_rate=0.0)

    login_key = RateLimitService.build_email_key("login", "attacker@test.com")
    signup_key = RateLimitService.build_email_key("signup", "attacker@test.com")

    login_res1 = await limiter.acquire(login_key)
    login_res2 = await limiter.acquire(login_key)
    signup_res1 = await limiter.acquire(signup_key)

    assert login_res1 is True
    assert login_res2 is False

    assert signup_res1 is True


# --------------------------------------------------------------------------------------
# Token Bucket Specific Tests
# --------------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_token_bucket_refill_over_time(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=2.0, refill_rate=1.0)

    result1 = await limiter.acquire("test_user")
    assert result1 is True
    result2 = await limiter.acquire("test_user")
    assert result2 is True
    result3 = await limiter.acquire("test_user")
    assert result3 is False

    await asyncio.sleep(1.1)

    result4 = await limiter.acquire("test_user")
    assert result4 is True


@pytest.mark.asyncio
async def test_token_bucket_capacity_limits_burst(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=3.0, refill_rate=1.0)

    results = []
    for _ in range(5):
        result = await limiter.acquire("test_user")
        results.append(result)

    assert results.count(True) == 3
    assert results.count(False) == 2


@pytest.mark.asyncio
async def test_token_bucket_partial_refill(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=2.0, refill_rate=1.0)

    result1 = await limiter.acquire("test_user")
    assert result1 is True
    result2 = await limiter.acquire("test_user")
    assert result2 is True
    result3 = await limiter.acquire("test_user")
    assert result3 is False

    await asyncio.sleep(0.5)

    result4 = await limiter.acquire("test_user")
    assert result4 is False

    await asyncio.sleep(0.6)

    result5 = await limiter.acquire("test_user")
    assert result5 is True


@pytest.mark.asyncio
async def test_token_bucket_stores_correct_state(test_redis_client, monkeypatch) -> None:
    monkeypatch.setattr("core.security.rate_limiter.redis_manager.redis_manager.client", test_redis_client)

    limiter = TokenBucket(capacity=5.0, refill_rate=1.0)

    result = await limiter.acquire("test_user")
    assert result is True

    raw_data = await test_redis_client.get("test_user")
    assert raw_data is not None
    tokens, last_update = raw_data.split(":")

    assert float(tokens) == pytest.approx(4.0, abs=1e-2)