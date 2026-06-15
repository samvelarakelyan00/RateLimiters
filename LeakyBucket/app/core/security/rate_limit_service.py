# Non-Standard libs
from fastapi import HTTPException
from fastapi import status


class RateLimitService:
    @staticmethod
    def normalize_email(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    def build_ip_key(endpoint: str, ip: str) -> str:
        return f"rate:{endpoint}:ip:{ip}"

    @staticmethod
    def build_email_key(endpoint: str, email: str) -> str:
        email = RateLimitService.normalize_email(email)

        return f"rate:{endpoint}:email:{email}"

    @staticmethod
    def raise_ip_limit() -> None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests from this IP."
        )

    @staticmethod
    def raise_email_limit() -> None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests for this account."
        )
