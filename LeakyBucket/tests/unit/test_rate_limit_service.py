# Non-Standard libs
import pytest
from fastapi import HTTPException

# Own Modules
from core.security.rate_limiter.rate_limit_service import RateLimitService


# --------------------------------------------------------------------------------------
# Email Normalization
# --------------------------------------------------------------------------------------
def test_normalize_email_lowercases() -> None:
    """
    Email should always be converted to lowercase.
    """
    result = RateLimitService.normalize_email("John.Doe@GMAIL.COM")

    assert result == "john.doe@gmail.com"


def test_normalize_email_strips_whitespace() -> None:
    """
    Leading and trailing whitespace should be removed.
    """
    result = RateLimitService.normalize_email("   test@gmail.com   ")

    assert result == "test@gmail.com"


def test_normalize_email_strips_and_lowercases() -> None:
    """
    Normalization should perform both strip and lowercase operations.
    """
    result = RateLimitService.normalize_email("   TeSt@GMAIL.Com   ")

    assert result == "test@gmail.com"


# --------------------------------------------------------------------------------------
# IP Key Generation
# --------------------------------------------------------------------------------------
def test_build_ip_key_login() -> None:
    """
    Login IP key should follow the expected format.
    """
    result = RateLimitService.build_ip_key(
        endpoint="login",
        ip="127.0.0.1"
    )

    assert result == "rate:login:ip:127.0.0.1"


def test_build_ip_key_signup() -> None:
    """
    Signup IP key should follow the expected format.
    """
    result = RateLimitService.build_ip_key(
        endpoint="signup",
        ip="192.168.1.10"
    )

    assert result == "rate:signup:ip:192.168.1.10"


# --------------------------------------------------------------------------------------
# Email Key Generation
# --------------------------------------------------------------------------------------
def test_build_email_key_format() -> None:
    """
    Email key should follow the expected format.
    """
    result = RateLimitService.build_email_key(
        endpoint="login",
        email="test@gmail.com"
    )

    assert result == "rate:login:email:test@gmail.com"


def test_build_email_key_normalizes_email() -> None:
    """
    Email key generation must normalize the email first.
    """
    result = RateLimitService.build_email_key(
        endpoint="login",
        email="   TeSt@GMAIL.COM   "
    )

    assert result == "rate:login:email:test@gmail.com"


# --------------------------------------------------------------------------------------
# HTTP Exceptions
# --------------------------------------------------------------------------------------
def test_raise_ip_limit_raises_http_exception() -> None:
    """
    IP limiter should raise HTTP 429.
    """
    with pytest.raises(HTTPException) as exc:
        RateLimitService.raise_ip_limit()

    assert exc.value.status_code == 429
    assert exc.value.detail == "Too many requests from this IP."


def test_raise_email_limit_raises_http_exception() -> None:
    """
    Email limiter should raise HTTP 429.
    """
    with pytest.raises(HTTPException) as exc:
        RateLimitService.raise_email_limit()

    assert exc.value.status_code == 429
    assert exc.value.detail == "Too many requests for this account."