# Non-Standard libs
from fastapi import Request

# Own Modules
from core.security.rate_limiter import RateLimitGuard
from core.security.rate_limiter.rate_limit_profiles import (
    LOGIN_IP_LIMITER, LOGIN_EMAIL_LIMITER,
    SIGNUP_IP_LIMITER, SIGNUP_EMAIL_LIMITER,
    DEFAULT_IP_LIMITER, DEFAULT_ACCOUNT_LIMITER
)

#
# def get_signup_rate_limiter() -> RateLimitGuard:
#     return RateLimitGuard("signup", SIGNUP_IP_LIMITER, SIGNUP_EMAIL_LIMITER)

async def get_signup_rate_limiter(
    request: Request
) -> None:

    guard = RateLimitGuard(
        "signup",
        SIGNUP_IP_LIMITER,
        SIGNUP_EMAIL_LIMITER
    )

    await guard(request)


async def get_login_rate_limiter(
    request: Request
) -> None:

    guard = RateLimitGuard(
        "login",
        LOGIN_IP_LIMITER,
        LOGIN_EMAIL_LIMITER
    )

    await guard(request)
