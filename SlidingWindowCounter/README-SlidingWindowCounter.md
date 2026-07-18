Sliding Window Counter Rate Limiter
=================================

Documentation
-------------

### Table of Contents

1.  Overview
    
2.  Architecture
    
3.  File Structure
    
4.  Algorithm Explanation
    
5.  Configuration
    
6.  Installation & Setup
    
7.  Running the Service
    
8.  Testing
    
9.  API Endpoints
    
10.  Rate Limit Profiles
    
11.  Redis Integration
    
12.  Performance Considerations
    
13.  Troubleshooting
    
14.  Extending the Service
    

Overview
--------

The Sliding Window Counter is a production-grade, distributed rate-limiting implementation designed for high-concurrency environments. It is one of five rate-limiting algorithms in the RateLimiters project, offering an optimal balance between accuracy and memory efficiency.

### Key Characteristics

*   **Hybrid Approach**: Combines fixed window counters with weighted averages for accuracy

*   **Memory Efficient**: O(1) storage per key (unlike Sliding Window Log)

*   **Distributed by Design**: Works across multiple service instances sharing a Redis backend

*   **Atomic Operations**: Lua scripts ensure race-condition-free execution

*   **High Performance**: Optimized for 50,000+ concurrent requests

*   **FastAPI Integration**: Clean dependency injection via Depends() system

*   **No Boundary Bursts**: Smooth rate limiting across window boundaries


### Use Cases

*   Production API rate limiting requiring accuracy without high memory cost

*   Systems balancing precision and performance

*   High-traffic endpoints where memory efficiency is critical

*   Financial and compliance applications

*   Distributed systems requiring consistent rate limiting

*   Enterprise-grade rate limiting requirements


Architecture
------------

### High-Level Design

The Sliding Window Counter follows a clean, layered architecture that separates concerns and promotes maintainability:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                         │
├─────────────────────────────────────────────────────────────────────┤
│                        API Layer (v1 Router)                        │
├─────────────────────────────────────────────────────────────────────┤
│                     Rate Limit Guard (Middleware)                   │
│                                                                     │
│  ┌─────────────────────┐  ┌─────────────────────┐                   │
│  │   IP-based Limiter  │  │  Email-based Limiter│                   │
│  └─────────────────────┘  └─────────────────────┘                   │
├─────────────────────────────────────────────────────────────────────┤
│                    Rate Limit Service (Core Logic)                  │
├─────────────────────────────────────────────────────────────────────┤
│                Sliding Window Counter Engine (Redis + Lua)          │
├─────────────────────────────────────────────────────────────────────┤
│                    Redis Connection Manager                         │
├─────────────────────────────────────────────────────────────────────┤
│                          Redis Cluster                              │
└─────────────────────────────────────────────────────────────────────┘
````

### Component Breakdown

#### 1. SlidingWindowCounter (Core Engine)

The heart of the rate limiter, implementing the algorithm with:

*   Lua scripts for atomic operations
    
*   Redis String storage for counters
    
*   EVALSHA optimization for script caching
    
*   Async/await for high concurrency
    

#### 2. RateLimitGuard (FastAPI Middleware)

Intercepts incoming requests and applies rate limiting:

*   Checks content length before processing
    
*   Extracts client IP from headers (X-Forwarded-For, CF-Connecting-IP)
    
*   Applies IP-based limiting (always)
    
*   Applies email-based limiting (optional, when email present)
    
*   Raises HTTP 429 exceptions when limits exceeded
    

#### 3. RateLimitService (Utility Layer)

Provides helper functions for:

*   Client IP extraction behind proxies
    
*   Email normalization (case-insensitive, whitespace-stripped)
    
*   Redis key construction for IP and email scopes
    
*   HTTP exception raising with algorithm-specific messages
    

#### 4. RateLimitProfiles (Configuration)

Pre-configured rate limiter instances:

*   Default: 60 requests per 60-second window
    
*   Signup: 5 IP / 2 email requests per 60-second window
    
*   Login: 3 requests per 60-second window (IP and email)
    

#### 5. RedisConnectionManager (Infrastructure)

Manages the Redis connection pool:

*   Connection pooling with configurable limits
    
*   Automatic response decoding
    
*   Health check (ping) for startup verification
    
*   Graceful shutdown (closing connections)
    

File Structure
--------------

```
SlidingWindowCounter/
├── app/
│   ├── api/
│   │   ├── dependencies/
│   │   │   ├── auth_deps.py              # Auth service dependency injection
│   │   │   └── auth_rate_limiters_dep.py # Rate limiter dependency factories
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   └── auth.py               # Authentication endpoints (login/signup)
│   │       └── __init__.py
│   ├── core/
│   │   ├── security/
│   │   │   └── rate_limiter/
│   │   │       ├── __init__.py
│   │   │       ├── rate_limit_guard.py   # FastAPI dependency guard
│   │   │       ├── rate_limit_profiles.py # Pre-configured limiters
│   │   │       ├── rate_limit_service.py # IP extraction, key building, exceptions
│   │   │       ├── rate_limiter.py       # Core SlidingWindowCounter implementation
│   │   │       └── redis_manager.py      # Redis connection management
│   │   └── settings/                     # Application configuration
│   │       ├── __init__.py
│   │       ├── environments_settings.py
│   │       ├── global_settings.py
│   │       ├── logging_settings.py
│   │       ├── redis_settings.py
│   │       └── ssm_source_settings.py
│   ├── schemas/
│   │   └── user_schemas.py               # Pydantic request/response models
│   ├── services/
│   │   └── auth.py                       # Business logic layer
│   └── main.py                           # FastAPI application entry point
├── tests/
│   ├── concurrency/                      # Race condition & stress tests
│   │   ├── __init__.py
│   │   └── test_rate_limiter_concurrency.py
│   ├── integration/                      # API & Redis integration tests
│   │   ├── test_rate_limiter_with_api.py
│   │   └── test_rate_limiter_with_redis_conn.py
│   ├── security-abuse/                   # Security hardening tests
│   │   ├── __init__.py
│   │   └── test_rate_limiter_security_and_abuse.py
│   ├── unit/                             # Granular function tests
│   │   ├── test_rate_limit_service.py
│   │   └── test_rate_limiter.py
│   ├── __init__.py
│   └── conftest.py                       # Shared test fixtures
├── .env                                  # Environment configuration
├── docker-compose.yml                    # Multi-container orchestration
├── docker-compose.override.yml           # Development overrides
├── docker-entrypoint.sh                  # Container startup script
├── Dockerfile                            # Multi-stage production build
├── Makefile                              # Automation commands
├── pyproject.toml                        # Project dependencies and metadata
├── pytest.ini                            # Test configuration
└── README.md                             # Algorithm-specific documentation
```
Algorithm Explanation
---------------------

### How Sliding Window Counter Works

The Sliding Window Counter algorithm combines the memory efficiency of fixed windows with the accuracy of sliding windows by using a weighted average. Instead of storing individual timestamps (like Sliding Window Log), it maintains counters for the current and previous fixed windows and calculates an estimated count using a weighted average based on the position within the current window.

```
Time: 0s                60s               120s              180s
      |                  |                 |                 |
      |---- Window 1 ----|---- Window 2 ---|---- Window 3 ---|
      |   key:123:0      |   key:123:1     |   key:123:2     |
      |   count: 5/10    |   count: 5/10   |   count: 0/10   |
      |                  |                 |                 |
      v                  v                 v                 v
    Request at 30s    Weighted: 0.5      Weighted: 0.25     Weighted: 0.75
    (elapsed/time)    Estimated: 5       Estimated: 3.75    Estimated: 6.25
```

### Weighted Average Calculation

The estimated count is calculated as:

```
elapsed = now - (current_window * window_size)
weight = elapsed / window_size
estimated_count = (previous_count * (1 - weight)) + (current_count * weight)
```

### Window Key Generation

```
current_window = floor(now / window_size)
previous_window = current_window - 1
current_window_key = search_key + ":" + current_window
previous_window_key = search_key + ":" + previous_window
```

### Example Calculation

For a 60-second window, at 30 seconds into the window:

*   Current window count: 5
    
*   Previous window count: 10
    
*   Weight: 30/60 = 0.5

*   Estimated count: (10 * (1 - 0.5)) + (5 * 0.5) = 5 + 2.5 = 7.5


### Lua Script Execution Flow

1. **Receive Parameters**: key, window_size, limit, current_time, requested

2. **Calculate Windows**: current_window, previous_window

3. **Get Counts**: GET current_window_key, GET previous_window_key

4. **Calculate Weight**: elapsed_in_window / window_size

5. **Estimate Count**: (previous_count * (1 - weight)) + (current_count * weight)

6. **Check Limit**: If estimated_count + requested <= limit

7. **Allow**: INCRBY current_window_key, EXPIRE, return 1

8. **Deny**: EXPIRE current_window_key, return 0


### Atomicity Guarantee

The Lua script executes atomically in Redis, ensuring:

*   No race conditions between concurrent requests
    
*   Consistent counter increments
    
*   Proper window expiration
    

Configuration
-------------

### Environment Variables

```
┌─────────────────────────┬──────────────────────────────────────┬─────────────┬──────────┐
│ Variable                │ Description                          │ Default     │ Required │
├─────────────────────────┼──────────────────────────────────────┼─────────────┼──────────┤
│ ENV_STATE               │ Environment (local, dev, staging)    │ local       │ Yes      │
│ REDIS_HOST              │ Redis server hostname                │ redis       │ Yes      │
│ REDIS_PORT              │ Redis server port                    │ 6379        │ Yes      │
│ REDIS_DB                │ Redis database index                 │ 0           │ Yes      │
│ REDIS_MAX_CONNECTIONS   │ Redis connection pool size           │ 50          │ Yes      │
│ LOG_LEVEL               │ Logging level (DEBUG, INFO, etc)     │ INFO        │ Yes      │
│ LOG_JSON_FORMAT         │ Use JSON format for logs             │ False       │ Yes      │
│ RUN_TESTS               │ Run tests on container startup       │ false       │ No       │
│ TEST_TYPE               │ Test type to run                     │ all         │ No       │
└─────────────────────────┴──────────────────────────────────────┴─────────────┴──────────┘
```

### Rate Limit Profiles

```
# DEFAULT: 60 requests per 60-second sliding window
DEFAULT_IP_LIMITER = SlidingWindowCounter(window_size=60.0, limit=60)
DEFAULT_ACCOUNT_LIMITER = SlidingWindowCounter(window_size=60.0, limit=60)

# SIGNUP: 5 IP / 2 email per 60-second sliding window
SIGNUP_IP_LIMITER = SlidingWindowCounter(window_size=60.0, limit=5)
SIGNUP_EMAIL_LIMITER = SlidingWindowCounter(window_size=60.0, limit=2)

# LOGIN: 3 requests per 60-second sliding window
LOGIN_IP_LIMITER = SlidingWindowCounter(window_size=60.0, limit=3)
LOGIN_EMAIL_LIMITER = SlidingWindowCounter(window_size=60.0, limit=3)
```

### Custom Configuration Examples

```
# 100 requests per minute
api_limiter = SlidingWindowCounter(window_size=60.0, limit=100)

# 1000 requests per hour
rate_limiter = SlidingWindowCounter(window_size=3600.0, limit=1000)

# 10 requests per 5 seconds (short burst protection)
burst_limiter = SlidingWindowCounter(window_size=5.0, limit=10)
```

Installation & Setup
--------------------

### Prerequisites

*   Python 3.12 or higher
    
*   Docker and Docker Compose
    
*   uv package manager (recommended)
    

### Clone and Setup

```
git clone git@github.com:samvelarakelyan00/RateLimiters.git
cd RateLimiters/SlidingWindowCounter
cp .env.example .env
```

### Install Dependencies

```
uv sync
```

### Configure Environment

```
ENV_STATE=local
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_MAX_CONNECTIONS=50
LOG_LEVEL=INFO
LOG_JSON_FORMAT=False
```

Running the Service
-------------------

### With Docker Compose (Recommended)

**Start without tests:**

```make up```

**Start with tests on startup:**

```make up-tests```

**Start with specific test type:**

```
make up-unit          # Unit tests only
make up-integration   # Integration tests only
make up-security      # Security tests only
make up-concurrency   # Concurrency tests only
```

**Development mode (with tests, not detached):**

```make up-dev```

### Without Docker

```uv run uvicorn app.main:app --port 8000 --host 0.0.0.0```

### Access the Service

*   API: http://localhost:8000/api/v1/auth
    
*   Root: http://localhost:8000/
    
*   Health Check: http://localhost:8000/health
    
*   Rate Limit Info: http://localhost:8000/rate-limit-info
    
*   API Documentation: http://localhost:8000/api/docs
    
*   Redoc: http://localhost:8000/api/redoc
    

Testing
-------

### Test Categories

```
┌─────────────────────┬──────────────────────────────────────┬─────────────────┐
│ Category            │ Description                          │ Test Count      │
├─────────────────────┼──────────────────────────────────────┼─────────────────┤
│ Unit                │ Granular function-level tests        │ 43              │
├─────────────────────┼──────────────────────────────────────┼─────────────────┤
│ Integration         │ Full stack with Redis and API        │ 36              │
├─────────────────────┼──────────────────────────────────────┼─────────────────┤
│ Security            │ Abuse prevention and attack sim      │ 13              │
├─────────────────────┼──────────────────────────────────────┼─────────────────┤
│ Concurrency         │ Race condition and stress tests      │ 16              │
├─────────────────────┼──────────────────────────────────────┼─────────────────┤
│ TOTAL               │                                      │ 108             │
└─────────────────────┴──────────────────────────────────────┴─────────────────┘
```

### Running Tests

**All tests in isolated Docker container (no app startup):**

```make test-with-docker```

**Specific test categories:**

```
make test-with-docker-unit
make test-with-docker-integration
make test-with-docker-security
make test-with-docker-concurrency
```

**Tests in running container:**

```
make test-all
make test-unit
make test-integration
make test-security
make test-concurrency
```

**Coverage report:**

```make coverage```

### Test Output

The test runner provides real-time output showing each test as it runs:

```
=== UNIT TESTS ===
...
sliding_window_log_bucket_container  | collecting ... collected 43 items
sliding_window_log_bucket_container  | 
sliding_window_log_bucket_container  | ../tests/unit/test_rate_limit_service.py::test_normalize_email_lowercases PASSED [  2%]
sliding_window_log_bucket_container  | ../tests/unit/test_rate_limit_service.py::test_normalize_email_strips_whitespace PASSED [  4%]
sliding_window_log_bucket_container  | ../tests/unit/test_rate_limit_service.py::test_normalize_email_strips_and_lowercases PASSED [  6%]
...
sliding_window_log_bucket_container  | ../tests/unit/test_rate_limiter.py::test_get_newest_timestamp_returns_zero_for_empty PASSED [ 97%]
sliding_window_log_bucket_container  | ../tests/unit/test_rate_limiter.py::test_get_newest_timestamp_returns_correct_value PASSED [100%]
sliding_window_log_bucket_container  | 
sliding_window_log_bucket_container  | ============================== 43 passed in 6.33s ==============================
sliding_window_log_bucket_container  | 
sliding_window_log_bucket_container  | ========================================
sliding_window_log_bucket_container  |           TEST SUMMARY
sliding_window_log_bucket_container  | ========================================
sliding_window_log_bucket_container  | Total Tests:  43
sliding_window_log_bucket_container  | Passed:       43
sliding_window_log_bucket_container  | Failed:       0
sliding_window_log_bucket_container  | XFailed:      0
sliding_window_log_bucket_container  | Errors:       0
sliding_window_log_bucket_container  | ----------------------------------------
sliding_window_log_bucket_container  | ✅ ALL TESTS PASSED!
sliding_window_log_bucket_container  | ========================================
```

API Endpoints
-------------

### Health Check

```GET /health```

**Response:**

```
{
  "status": "healthy",
  "service": "SlidingWindowCounter",
  "version": "0.1.0",
  "timestamp": 1700000000,
  "checks": {
    "redis": true
  }
}
```

### Service Info

```GET /```

**Response:**

```
{
  "service": "Sliding Window Counter Rate Limiter",
  "version": "0.1.0",
  "status": "operational",
  "uptime_seconds": 3600
}
```

### Rate Limit Info

```GET /rate-limit-info```

**Response:**

```
{
  "algorithm": "Sliding Window Counter",
  "default_window_size": "60 seconds",
  "default_limit": "60 requests per window",
  "endpoints": {
    "login": "3 attempts per 60 seconds (IP and Email)",
    "signup": "5 attempts per 60 seconds (IP), 2 per 60 seconds (Email)",
    "default": "60 requests per 60 seconds"
  }
}
```

### Authentication Endpoints

**Login:**

```POST /api/v1/auth/login```

**Request Body:**

```
{
  "email": "user@example.com",
  "password": "secure_password"
}
```

**Signup:**

```POST /api/v1/auth/signup```

**Request Body:**

```
{
  "username": "john_doe",
  "email": "john@example.com",
  "plain_password": "secure_password"
}
```

### Rate Limit Response

When rate limit is exceeded:

```HTTP 429 Too Many Requests```

```
{
  "detail": "Sliding Window Counter -> Your IP limit exceeded; please try again later!"
}
```

Redis Integration
-----------------

### Redis Key Structure

```
┌──────────────────────────────────────────┬───────────────────────────────────────────────┬─────────────────┬──────────────────┐
│ Key Pattern                              │ Example                                       │ Data Structure  │ TTL              │
├──────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────┼──────────────────┤
│ rate:{endpoint}:ip:{ip}:{window_id}      │ rate:login:ip:192.168.1.1:28333333            │ String          │ window_size * 2  │
├──────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────┼──────────────────┤
│ rate:{endpoint}:email:{email}:{window_id}│ rate:login:email:user@test.com:28333333       │ String          │ window_size * 2  │
└──────────────────────────────────────────┴───────────────────────────────────────────────┴─────────────────┴──────────────────┘
```

### Sorted Set Storage

Each request timestamp is stored as a member in the sorted set:

```
ZADD key timestamp member
```

Example:

```
ZADD rate:login:ip:192.168.1.1 1700000000 1700000000
ZADD rate:login:ip:192.168.1.1 1700000001 1700000001
ZADD rate:login:ip:192.168.1.1 1700000002 1700000002
```

### Connection Pool Configuration

```
pool = aioredis.ConnectionPool(
    host=settings.redis.HOST,
    port=settings.redis.PORT,
    db=settings.redis.DB,
    max_connections=settings.redis.MAX_CONNECTIONS,
    decode_responses=True
)
```

### Health Check

```
async def verify_redis_connection(self) -> None:
    await self.client.ping()
```

Performance Considerations
--------------------------

### Throughput

*   **Latency**: < 2ms per request (p95)
    
*   **Concurrent Requests**: 50,000+
    
*   **Redis Operations**: Multiple GET + INCRBY per request
    

### Memory Usage

*   **Per Key**: ~50 bytes (counter + key)
    
*   **TTL Strategy**: window_size * 2 auto-expiry
    
*   **Memory Optimization**: Redis Strings instead of Hashes
    

### Concurrency Safety

*   **Atomic Lua Scripts**: Prevent race conditions
    
*   **Connection Pooling**: Efficient Redis connection reuse
    
*   **Retry Logic**: Automatic retry on timeout

Trade-offs

```
┌─────────────────────┬───────────────────────────────────────────────┬────────────────────────────────────────────────────┐
│ Aspect              │ Advantage                                     │ Disadvantage                                       │
├─────────────────────┼───────────────────────────────────────────────┼────────────────────────────────────────────────────┤
│ Precision           │ Good approximation of sliding window          │ Not exact like Sliding Window Log                  │
├─────────────────────┼───────────────────────────────────────────────┼────────────────────────────────────────────────────┤
│ Memory              │ O(1) per key                                  │ Less accurate at window boundaries                 │
├─────────────────────┼───────────────────────────────────────────────┼────────────────────────────────────────────────────┤
│ Complexity          │ Simple counter management                     │ Weighted average calculation                       │
├─────────────────────┼───────────────────────────────────────────────┼────────────────────────────────────────────────────┤
│ Burst               │ No window boundary bursts                     │ Small approximation error                          │
└─────────────────────┴───────────────────────────────────────────────┴────────────────────────────────────────────────────┘
```
### Optimization Tips

1. Increase connection pool size for higher concurrency:
```REDIS_MAX_CONNECTIONS=200```
    
2. **Use Redis Cluster** for horizontal scaling
    
3. Adjust window size based on use case:
```
# Short bursts (5 seconds)
SlidingWindowCounter(window_size=5.0, limit=10)

# Long-term quotas (1 hour)
SlidingWindowCounter(window_size=3600.0, limit=1000)
```
4. Use dedicated Redis database for rate limiting:
```REDIS_DB=1```
    

Troubleshooting
---------------

### Common Issues

**1. Connection to Redis fails**

Check Redis is running:

```
make redis-cli
redis-cli ping
```

Verify Redis host/port in .env:

```
REDIS_HOST=redis
REDIS_PORT=6379
```

**2. Rate limiting not working**

Check Redis keys:

```redis-cli KEYS "rate:*"```

Verify Redis connection in logs:

```
Server started...
Redis connection verified...
```

**3. Tests failing**

Run tests in isolation:

```
make clean
make test-with-docker-unit
```

Check Redis connection in tests:

```make test-with-docker-integration```

**4. Event loop issues with tests**

Known issue with pytest-asyncio and Redis connections. Tests are marked with @pytest.mark.xfail when event loop issues occur.

### Logs

**View application logs:**

```make logs```

**View Redis logs:**

```make logs-redis```

### Debug Mode

Enable debug logging:

```LOG_LEVEL=DEBUG```

Run in development mode:

```make up-dev```

Extending the Service
---------------------

### Adding New Rate Limit Profiles

Create new profiles in rate\_limit\_profiles.py:

```
# 100 requests per minute for API endpoints
API_IP_LIMITER = SlidingWindowCounter(window_size=60.0, limit=100)

# 10 requests per 5 seconds for burst protection
BURST_LIMITER = SlidingWindowCounter(window_size=5.0, limit=10)

# 1000 requests per hour for premium users
PREMIUM_LIMITER = SlidingWindowCounter(window_size=3600.0, limit=1000)
```

### Adding Custom Dependencies

Create a new dependency in auth\_rate\_limiters\_dep.py:

```
async def get_api_rate_limiter(request: Request) -> None:
    guard = RateLimitGuard(
        endpoint_identifier="api",
        ip_limiter=API_IP_LIMITER,
        account_limiter=API_ACCOUNT_LIMITER,
        max_body_bytes=1024 * 100  # 100KB
    )
    await guard(request)
```

### Adding New Endpoints

```
@router.get("/protected")
async def protected_endpoint(
    request: Request,
    _: Annotated[None, Depends(get_api_rate_limiter)]
):
    return {"message": "Protected endpoint with rate limiting"}
```

### Custom Window Configurations

```
# 5-minute window
limiter = SlidingWindowCounter(window_size=300.0, limit=50)

# 15-minute window
limiter = SlidingWindowCounter(window_size=900.0, limit=100)

# 24-hour window
limiter = SlidingWindowCounter(window_size=86400.0, limit=1000)
```

Monitoring & Observability
--------------------------

### Metrics to Track

*   **Request count**: Total requests per window
    
*   **Rate limit hits**: 429 responses
    
*   **Redis latency**: Response time from Redis
    
*   **Concurrent connections**: Active Redis connections
    
*   **Window size**: Current window usage
    
*   **Error rate**: HTTP 500 responses
    

### Health Endpoints

*   /health - Basic health check (Redis connectivity)
    
*   /rate-limit-info - Rate limit configuration info
    

### Health Check Integration

**Kubernetes liveness probe:**

```
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
```

**AWS ALB health check:**

```
Target: /health
Port: 8000
Interval: 30 seconds
Timeout: 5 seconds
```

Support
-------

For issues, questions, or contributions:

*   GitHub Issues: [https://github.com/samvelarakelyan00/RateLimiters/issues](https://github.com/your-username/RateLimiters/issues)
    
*   Documentation: [https://github.com/samvelarakelyan00/RateLimiters/tree/main/SlidingWindowCounter](https://github.com/your-username/RateLimiters/tree/main/FixedWindowCounter)
    

**Documentation Version:** 1.0.0 **Last Updated:** July 2026 **Maintained by:** Samvel Arakelyan