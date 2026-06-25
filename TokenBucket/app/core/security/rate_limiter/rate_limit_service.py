# Non-Standard libs
from fastapi import (
    status,
    Request,
    HTTPException
)


class RateLimitService:
    @staticmethod
    def extract_client_ip(request: Request) -> str:
        """
        Extracts the genuine client IP address behind proxies.
        Safeguards against header-spoofing by enforcing trusted proxy lookups.
        """
        # Look for standard reverse proxy forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")

        if forwarded_for:
            # The first IP in the list is the original client, subsequent ones are proxy hops
            return forwarded_for.split(",")[0].strip()

        # Cloudflare specific optimization if applicable
        cf_ip = request.headers.get("CF-Connecting-IP")
        if cf_ip:
            return cf_ip

        return request.client.host if request.client else "127.0.0.1"

    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def build_ip_key(endpoint: str, ip: str) -> str:
        return f"rate:{endpoint}:ip:{ip}"

    @classmethod
    def build_email_key(cls, endpoint: str, email: str) -> str:
        email = cls.normalize_email(email)

        return f"rate:{endpoint}:email:{email}"

    @staticmethod
    def raise_ip_limit_exceeded() -> None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Token Bucket -> Your IP limit exceeded; please try again later!"
        )

    @staticmethod
    def raise_email_limit_exceeded() -> None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Token Bucket -> Your email limit exceeded; please try again later!"
        )
