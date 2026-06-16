import pytest

from core.security.rate_limit_profiles import (
    LOGIN_IP_LIMITER,
    LOGIN_EMAIL_LIMITER,
    SIGNUP_IP_LIMITER,
    SIGNUP_EMAIL_LIMITER,
)


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    LOGIN_IP_LIMITER._buckets.clear()
    LOGIN_EMAIL_LIMITER._buckets.clear()
    SIGNUP_IP_LIMITER._buckets.clear()
    SIGNUP_EMAIL_LIMITER._buckets.clear()

    yield

    LOGIN_IP_LIMITER._buckets.clear()
    LOGIN_EMAIL_LIMITER._buckets.clear()
    SIGNUP_IP_LIMITER._buckets.clear()
    SIGNUP_EMAIL_LIMITER._buckets.clear()