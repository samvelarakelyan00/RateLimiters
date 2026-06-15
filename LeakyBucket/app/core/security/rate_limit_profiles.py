# Own Modules
from core.security.rate_limiter import LeakyBucketLimiter


LOGIN_IP_LIMITER = LeakyBucketLimiter(
    capacity=1,
    leak_rate=0.5
)

LOGIN_EMAIL_LIMITER = LeakyBucketLimiter(
    capacity=3,
    leak_rate=0.2
)

SIGNUP_IP_LIMITER = LeakyBucketLimiter(
    capacity=3,
    leak_rate=0.2
)

SIGNUP_EMAIL_LIMITER = LeakyBucketLimiter(
    capacity=1,
    leak_rate=0.1
)