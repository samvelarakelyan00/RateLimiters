from core.security.rate_limiter.rate_limiter import TokenBucket


DEFAULT_IP_LIMITER = TokenBucket(capacity=60.0, refill_rate=1.0)
DEFAULT_ACCOUNT_LIMITER = TokenBucket(capacity=60.0, refill_rate=1.0)

SIGNUP_IP_LIMITER = TokenBucket(capacity=5.0, refill_rate=0.2)
SIGNUP_EMAIL_LIMITER = TokenBucket(capacity=2.0, refill_rate=0.1)

LOGIN_IP_LIMITER = TokenBucket(capacity=3.0, refill_rate=0.5)
LOGIN_EMAIL_LIMITER = TokenBucket(capacity=3.0, refill_rate=0.2)
