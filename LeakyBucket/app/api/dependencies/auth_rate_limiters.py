# Non-Standard libs
from fastapi import Request

# Own Modules
from core.security.rate_limit_profiles import (
    LOGIN_IP_LIMITER,
    LOGIN_EMAIL_LIMITER,
    SIGNUP_IP_LIMITER,
    SIGNUP_EMAIL_LIMITER
)

from core.security.rate_limit_service import (
    RateLimitService
)


class AuthRateLimitGuard:
    def __init__(self, endpoint_identifier: str) -> None:
        self.endpoint_identifier = endpoint_identifier

    async def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"

        if self.endpoint_identifier == "login":
            ip_limiter = LOGIN_IP_LIMITER
            email_limiter = LOGIN_EMAIL_LIMITER
        else:
            ip_limiter = SIGNUP_IP_LIMITER
            email_limiter = SIGNUP_EMAIL_LIMITER

        ip_key = RateLimitService.build_ip_key(self.endpoint_identifier, client_ip)

        if await ip_limiter.acquire(ip_key):
            RateLimitService.raise_ip_limit()

        body = await request.json()
        email = body.get("email")

        if not email:
            return

        email_key = RateLimitService.build_email_key(self.endpoint_identifier, email)

        if await email_limiter.acquire(email_key):
            RateLimitService.raise_email_limit()
