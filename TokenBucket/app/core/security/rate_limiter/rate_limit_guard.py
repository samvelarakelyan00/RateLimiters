# Standard libs
from typing import Optional

# Non-Standard libs
from fastapi import (
    status,
    Request,
    HTTPException
)

# Own Modules
from core.security.rate_limiter.rate_limiter import TokenBucket
from core.security.rate_limiter.rate_limit_service import RateLimitService


class RateLimitGuard:
    def __init__(self,
                 endpoint_identifier: str,
                 ip_limiter: TokenBucket,
                 account_limiter: Optional[TokenBucket] = None,
                 max_body_bytes: int = 1024 * 50
            ) -> None:

        self.endpoint_identifier = endpoint_identifier
        self.ip_limiter = ip_limiter
        self.account_limiter = account_limiter
        self.max_body_bytes = max_body_bytes

    async def __call__(self, request: Request) -> None:
        content_length = request.headers.get("content-length")

        if content_length and int(content_length) > self.max_body_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"The content length should be less than or equal to {self.max_body_bytes} MB"
            )

        client_ip = RateLimitService.extract_client_ip(request)
        ip_key = RateLimitService.build_ip_key(self.endpoint_identifier, client_ip)

        if not await self.ip_limiter.acquire(ip_key):
            RateLimitService.raise_ip_limit_exceeded()

        if not self.account_limiter:
            return

        try:
            body = await request.json()
        except Exception as err:
            raise err

        email = body.get("email")

        if not email:
            return

        email_key = RateLimitService.build_email_key(self.endpoint_identifier, email)

        if not await self.account_limiter.acquire(email_key):
            RateLimitService.raise_email_limit_exceeded()
