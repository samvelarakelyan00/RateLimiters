# Own modules
from core.security.rate_limiter.rate_limiter import LeakyBucketLimiter


LOGIN_IP_LIMITER = LeakyBucketLimiter(capacity=1, leak_rate=0.5)
LOGIN_EMAIL_LIMITER = LeakyBucketLimiter(capacity=3, leak_rate=0.2)

SIGNUP_IP_LIMITER = LeakyBucketLimiter(capacity=3, leak_rate=0.2)
SIGNUP_EMAIL_LIMITER = LeakyBucketLimiter(capacity=1, leak_rate=0.1)

DEFAULT_IP_LIMITER = LeakyBucketLimiter(capacity=60, leak_rate=1.0)
DEFAULT_ACCOUNT_LIMITER = LeakyBucketLimiter(capacity=100, leak_rate=2.0)
