from core.security.rate_limiter.rate_limiter import FixedWindowCounter

# =============================================================================
# Default Limiters
# =============================================================================
# General purpose rate limiters for standard endpoints
# 60 requests per 60-second window (1 request per second average)
DEFAULT_IP_LIMITER = FixedWindowCounter(window_size=60.0, limit=60)
DEFAULT_ACCOUNT_LIMITER = FixedWindowCounter(window_size=60.0, limit=60)

# =============================================================================
# Signup Limiters
# =============================================================================
# More restrictive limits for account creation to prevent abuse
# Signup IP: 5 signups per 60-second window (1 per 12 seconds average)
SIGNUP_IP_LIMITER = FixedWindowCounter(window_size=60.0, limit=5)

# Signup Email: 2 signups per 60-second window (1 per 30 seconds average)
SIGNUP_EMAIL_LIMITER = FixedWindowCounter(window_size=60.0, limit=2)

# =============================================================================
# Login Limiters
# =============================================================================
# Stricter limits for authentication endpoints to prevent brute force
# Login IP: 3 attempts per 60-second window (1 per 20 seconds average)
LOGIN_IP_LIMITER = FixedWindowCounter(window_size=60.0, limit=3)

# Login Email: 3 attempts per 60-second window (1 per 20 seconds average)
LOGIN_EMAIL_LIMITER = FixedWindowCounter(window_size=60.0, limit=3)


# =============================================================================
# Optional: Additional Common Profiles
# =============================================================================
# These can be uncommented and used as needed

# API Rate Limits
# API_IP_LIMITER = FixedWindowCounter(window_size=60.0, limit=100)
# API_ACCOUNT_LIMITER = FixedWindowCounter(window_size=60.0, limit=1000)

# Public Endpoint Limits
# PUBLIC_IP_LIMITER = FixedWindowCounter(window_size=60.0, limit=30)

# Admin Endpoint Limits (more permissive)
# ADMIN_IP_LIMITER = FixedWindowCounter(window_size=60.0, limit=200)

# High-Security Endpoints (very restrictive)
# SECURE_IP_LIMITER = FixedWindowCounter(window_size=300.0, limit=5)  # 5 per 5 minutes
# SECURE_ACCOUNT_LIMITER = FixedWindowCounter(window_size=300.0, limit=5)


# =============================================================================
# Utility Class for Predefined Window Sizes
# =============================================================================
class WindowSizes:
    """Common window sizes in seconds for reference."""
    SECONDS_1 = 1.0
    SECONDS_5 = 5.0
    SECONDS_15 = 15.0
    SECONDS_30 = 30.0
    MINUTE_1 = 60.0
    MINUTES_5 = 300.0
    MINUTES_15 = 900.0
    MINUTES_30 = 1800.0
    HOUR_1 = 3600.0
    DAY_1 = 86400.0


class RateLimitPresets:
    """
    Pre-defined rate limit configurations for common use cases.
    """

    @staticmethod
    def per_minute(limit: int) -> FixedWindowCounter:
        """Create a rate limiter with per-minute window."""
        return FixedWindowCounter(window_size=WindowSizes.MINUTE_1, limit=limit)

    @staticmethod
    def per_second(limit: int) -> FixedWindowCounter:
        """Create a rate limiter with per-second window."""
        return FixedWindowCounter(window_size=WindowSizes.SECONDS_1, limit=limit)

    @staticmethod
    def per_hour(limit: int) -> FixedWindowCounter:
        """Create a rate limiter with per-hour window."""
        return FixedWindowCounter(window_size=WindowSizes.HOUR_1, limit=limit)

    @staticmethod
    def per_day(limit: int) -> FixedWindowCounter:
        """Create a rate limiter with per-day window."""
        return FixedWindowCounter(window_size=WindowSizes.DAY_1, limit=limit)