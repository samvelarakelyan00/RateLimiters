from core.security.rate_limiter.rate_limiter import LeakyBucket


DEFAULT_IP_LIMITER = LeakyBucket(capacity=60, leak_rate=1.0)
DEFAULT_ACCOUNT_LIMITER = LeakyBucket(capacity=60.0, leak_rate=1.0)

SIGNUP_IP_LIMITER = LeakyBucket(capacity=5.0, leak_rate=0.2)
SIGNUP_EMAIL_LIMITER = LeakyBucket(capacity=2.0, leak_rate=0.1)

LOGIN_IP_LIMITER = LeakyBucket(capacity=3.0, leak_rate=0.5)
LOGIN_EMAIL_LIMITER = LeakyBucket(capacity=3.0, leak_rate=0.2)
