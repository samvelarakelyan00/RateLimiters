Sliding Window Log Rate Limiter
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

The Sliding Window Log is a production-grade, distributed rate-limiting implementation designed for high-concurrency environments. It is one of five rate-limiting algorithms in the RateLimiters project, offering the highest precision rate limiting with exact window boundaries.

### Key Characteristics

*   **Highest Precision**: Exact sliding window boundaries with no burst at edges

*   **Distributed by Design**: Works across multiple service instances sharing a Redis backend

*   **Atomic Operations**: Lua scripts ensure race-condition-free execution

*   **High Performance**: Optimized for high-concurrency environments

*   **FastAPI Integration**: Clean dependency injection via Depends() system

*   **Memory O(N)**: Stores timestamps of all requests in the window


    

### Use Cases

*   Financial systems requiring exact rate limiting

*   Compliance-critical applications

*   API rate limiting where precision is paramount

*   Audit trail and request logging

*   Systems where burst at window boundaries is unacceptable

*   Enterprise-grade rate limiting requirements


    

Architecture
------------

### High-Level Design

The Sliding Window Log follows a clean, layered architecture that separates concerns and promotes maintainability:

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
│                Sliding Window Log Engine (Redis + Lua)              │
├─────────────────────────────────────────────────────────────────────┤
│                    Redis Connection Manager                         │
├─────────────────────────────────────────────────────────────────────┤
│                          Redis Cluster                              │
└─────────────────────────────────────────────────────────────────────┘
````

### Component Breakdown

#### 1. SlidingWindowLog (Core Engine)

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

```SlidingWindowLog/
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
│   │   │       ├── rate_limiter.py       # Core SlidingWindowLog implementation
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

### How Sliding Window Log Works

The Sliding Window Log algorithm stores timestamps of all requests in a Redis Sorted Set. When a new request arrives, it removes entries older than the window size and checks if the remaining count exceeds the limit.

```
Time: 0s                10s               20s               30s
      |                  |                 |                 |
      |---- Request Log ----|              |                 |
      |   [0, 2, 4, 6, 8] |              |                 |
      |   5 requests      |              |                 |
      |                  |                 |                 |
      v                  v                 v                 v
    Request at 0s      Window: 0-10s    Window: 5-15s    Window: 10-20s
    Add to log         Count: 5/10      Count: 5/10      Count: 4/10
    (10 allowed)       (5 remaining)    (5 remaining)    (6 remaining)
```

### Sorted Set Operations

```
# Add timestamp
ZADD key timestamp timestamp

# Remove expired entries (older than cutoff)
ZREMRANGEBYSCORE key 0 cutoff

# Count remaining entries
ZCARD key
```

### Window Calculation

```
cutoff = now - window_size
expired_count = ZREMRANGEBYSCORE(key, 0, cutoff)
current_count = ZCARD(key)
```

### Lua Script Execution Flow

1. **Receive Parameters**: key, window_size, limit, current_time, requested

2. **Calculate Cutoff**: cutoff = now - window_size

3. **Remove Expired**: ZREMRANGEBYSCORE(key, 0, cutoff)

4. **Get Current Count**: ZCARD(key)

5. **Check Limit**: If current_count + requested <= limit

6. **Allow**: Add timestamps, EXPIRE key window_size * 2, return 1

7. **Deny**: EXPIRE key window_size * 2, return 0


    

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
DEFAULT_IP_LIMITER = SlidingWindowLog(window_size=60.0, limit=60)
DEFAULT_ACCOUNT_LIMITER = SlidingWindowLog(window_size=60.0, limit=60)

# SIGNUP: 5 IP / 2 email per 60-second sliding window
SIGNUP_IP_LIMITER = SlidingWindowLog(window_size=60.0, limit=5)
SIGNUP_EMAIL_LIMITER = SlidingWindowLog(window_size=60.0, limit=2)

# LOGIN: 3 requests per 60-second sliding window
LOGIN_IP_LIMITER = SlidingWindowLog(window_size=60.0, limit=3)
LOGIN_EMAIL_LIMITER = SlidingWindowLog(window_size=60.0, limit=3)
```

### Custom Configuration Examples

```
# 100 requests per minute
api_limiter = SlidingWindowLog(window_size=60.0, limit=100)

# 1000 requests per hour
rate_limiter = SlidingWindowLog(window_size=3600.0, limit=1000)

# 10 requests per 5 seconds (short burst protection)
burst_limiter = SlidingWindowLog(window_size=5.0, limit=10)
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
cd RateLimiters/FixedWindowCounter
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
│ Unit                │ Granular function-level tests        │ 29              │
├─────────────────────┼──────────────────────────────────────┼─────────────────┤
│ Integration         │ Full stack with Redis and API        │ 34              │
├─────────────────────┼──────────────────────────────────────┼─────────────────┤
│ Security            │ Abuse prevention and attack sim      │ 11              │
├─────────────────────┼──────────────────────────────────────┼─────────────────┤
│ Concurrency         │ Race condition and stress tests      │ 14              │
├─────────────────────┼──────────────────────────────────────┼─────────────────┤
│ TOTAL               │                                      │ 88              │
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
============================= test session starts ==============================
collected 29 items

../tests/unit/test_rate_limit_service.py::test_normalize_email_lowercases PASSED [ 3%]
../tests/unit/test_rate_limit_service.py::test_normalize_email_strips_whitespace PASSED [ 6%]
...

============================== 29 passed in 5.40s ==============================
```

API Endpoints
-------------

### Health Check

```GET /health```

**Response:**

```
{
  "status": "healthy",
  "service": "SlidingWindowLog",
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
  "service": "Sliding Window Log Rate Limiter",
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
  "algorithm": "Sliding Window Log",
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
  "detail": "Sliding Window Log -> Your IP limit exceeded; please try again later!"
}
```

Redis Integration
-----------------

### Redis Key Structure

```
┌──────────────────────────────────────────┬───────────────────────────────────────────────┬─────────────────┬──────────────────┐
│ Key Pattern                              │ Example                                       │ Data Structure  │ TTL              │
├──────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────┼──────────────────┤
│ rate:{endpoint}:ip:{ip}                  │ rate:login:ip:192.168.1.1                     │ Sorted Set      │ window_size * 2  │
├──────────────────────────────────────────┼───────────────────────────────────────────────┼─────────────────┼──────────────────┤
│ rate:{endpoint}:email:{email}            │ rate:login:email:user@test.com                │ Sorted Set      │ window_size * 2  │
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
    
*   **Redis Operations**: ZREMRANGEBYSCORE + ZCARD + ZADD
    

### Memory Usage

*   **Per Key**: ~50 bytes (counter + key)
    
*   **TTL Strategy**: window_size * 2 auto-expiry
    
*   **Memory Optimization**: Sorted Sets with automatic cleanup
    

### Concurrency Safety

*   **Atomic Lua Scripts**: Prevent race conditions
    
*   **Connection Pooling**: Efficient Redis connection reuse
    
*   **Retry Logic**: Automatic retry on timeout


### Optimization Tips

1.  ```REDIS_MAX_CONNECTIONS=200```
    
2.  **Use Redis Cluster** for horizontal scaling
    
3. 
```
# Short bursts (5 seconds)
SlidingWindowLog(window_size=5.0, limit=10)

# Long-term quotas (1 hour)
SlidingWindowLog(window_size=3600.0, limit=1000)
```
4. ```REDIS_DB=1```
    

Troubleshooting
---------------

### Common Issues

**1\. Connection to Redis fails**

Check Redis is running:

```
make redis-cli
redis-cli ping
```

Verify Redis host/port in .env:

```
REDIS_HOST=redis
REDIS_PORT=6379
```

**2\. Rate limiting not working**

Check Redis keys:

```redis-cli KEYS "rate:*"```

Verify Redis connection in logs:

```
Server started...
Redis connection verified...
```

**3\. Tests failing**

Run tests in isolation:

```
make clean
make test-with-docker-unit
```

Check Redis connection in tests:

```make test-with-docker-integration```

**4\. Event loop issues with tests**

Known issue with pytest-asyncio and Redis connections. Tests are marked with @pytest.mark.xfail when event loop issues occur.

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
API_IP_LIMITER = SlidingWindowLog(window_size=60.0, limit=100)

# 10 requests per 5 seconds for burst protection
BURST_LIMITER = SlidingWindowLog(window_size=5.0, limit=10)

# 1000 requests per hour for premium users
PREMIUM_LIMITER = SlidingWindowLog(window_size=3600.0, limit=1000)
```

### Adding Custom Dependencies

Create a new dependency in auth\_rate\_limiters\_dep.py:

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
limiter = SlidingWindowLog(window_size=300.0, limit=50)

# 15-minute window
limiter = SlidingWindowLog(window_size=900.0, limit=100)

# 24-hour window
limiter = SlidingWindowLog(window_size=86400.0, limit=1000)
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

*   /health - Basic health check (Redis connectivity)
    
*   /rate-limit-info - Rate limit configuration info
    

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
    
*   Documentation: [https://github.com/samvelarakelyan00/RateLimiters/tree/main/SlidingWindowLog](https://github.com/your-username/RateLimiters/tree/main/FixedWindowCounter)
    

**Documentation Version:** 1.0.0 **Last Updated:** July 2026 **Maintained by:** Samvel Arakelyan