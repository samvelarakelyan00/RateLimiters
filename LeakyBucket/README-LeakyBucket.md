Leaky Bucket Rate Limiter
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

The Leaky Bucket is a production-grade, distributed rate-limiting implementation designed for high-concurrency environments. It is one of five rate-limiting algorithms in the RateLimiters project, offering smooth traffic shaping with predictable request processing.

### Key Characteristics

*   **Smooth Traffic Shaping**: Processes requests at a constant, predictable rate

*   **Distributed by Design**: Works across multiple service instances sharing a Redis backend

*   **Atomic Operations**: Lua scripts ensure race-condition-free execution

*   **High Performance**: Optimized for 50,000+ concurrent requests

*   **FastAPI Integration**: Clean dependency injection via Depends() system

*   **Memory Efficient**: O(1) storage per key using Redis Strings
    

### Use Cases

*   API rate limiting with consistent request flow

*   Batch processing throttling

*   Downstream service protection

*   Queue management and load smoothing

*   Cost control for paid APIs

*   Compliance with usage SLAs
    

Architecture
------------

### High-Level Design

The Leaky Bucket follows a clean, layered architecture that separates concerns and promotes maintainability:

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                          │
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
│                    Leaky Bucket Engine (Redis + Lua)                │
├─────────────────────────────────────────────────────────────────────┤
│                    Redis Connection Manager                         │
├─────────────────────────────────────────────────────────────────────┤
│                          Redis Cluster                              │
└─────────────────────────────────────────────────────────────────────┘
````

### Component Breakdown

#### 1. LeakyBucket (Core Engine)

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
LeakyBucket/
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
│   │   │       ├── rate_limiter.py       # Core LeakyBucket implementation
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

### How Leaky Bucket Works

The Leaky Bucket algorithm works like a bucket with a hole at the bottom. Water (requests) is added to the bucket at varying rates, but it leaks out at a constant rate. If the bucket overflows, excess requests are denied.

```
Time: 0s                5s                10s               15s
      |                  |                 |                 |
      |---- Water ----   |---- Water ----  |---- Water ---- |
      |   Bucket: 3/5    |   Bucket: 2/5   |   Bucket: 1/5   |
      |                  |                 |                 |
      v                  v                 v                 v
    Request 1         Leak 1 unit       Leak 1 unit       Leak 1 unit
    Add 1 water       Request 4         Request 5         Request 6
    (4 remaining)     Add 1 water       Add 1 water       Add 1 water
                      (3 remaining)     (2 remaining)     (1 remaining)
```

### Water Level Calculation

```
elapsed = now - last_update
leaked = elapsed * leak_rate
water_level = max(0.0, water_level - leaked)
```

### Bucket State Storage

The bucket state is stored as a Redis String in the format:

```
"water_level:last_update"
```

Example: "3:1700000000" means 3 units of water at timestamp 1700000000.


### Lua Script Execution Flow

1. **Receive Parameters**: key, capacity, leak_rate, current_time, requested_water

2. **Get Current State**: GET key (returns "water_level:last_update")

3. **Calculate Leak**: elapsed * leak_rate, then max(0.0, water_level - leaked)

4. **Check Capacity**: If water_level + requested <= capacity

5. **Allow**: water_level = water_level + requested, SET key "water_level:now" EX 3600, return 1

6. **Deny**: SET key "water_level:now" EX 3600, return 0
    

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
# DEFAULT: 60 capacity, leak rate 1 water unit/second
DEFAULT_IP_LIMITER = LeakyBucket(capacity=60.0, leak_rate=1.0)
DEFAULT_ACCOUNT_LIMITER = LeakyBucket(capacity=60.0, leak_rate=1.0)

# SIGNUP: 5 IP / 2 email capacity with slower leak
SIGNUP_IP_LIMITER = LeakyBucket(capacity=5.0, leak_rate=0.2)
SIGNUP_EMAIL_LIMITER = LeakyBucket(capacity=2.0, leak_rate=0.1)

# LOGIN: 3 capacity with moderate leak
LOGIN_IP_LIMITER = LeakyBucket(capacity=3.0, leak_rate=0.5)
LOGIN_EMAIL_LIMITER = LeakyBucket(capacity=3.0, leak_rate=0.2)
```

### Custom Configuration Examples

```
# 100 capacity, leak 2 per second (high throughput)
api_limiter = LeakyBucket(capacity=100.0, leak_rate=2.0)

# 10 capacity, leak 0.1 per second (very restrictive)
rate_limiter = LeakyBucket(capacity=10.0, leak_rate=0.1)

# 50 capacity, leak 5 per second (fast processing)
burst_limiter = LeakyBucket(capacity=50.0, leak_rate=5.0)
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
cd RateLimiters/LeakyBucket
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
│ Unit                │ Granular function-level tests        │ 26              │
├─────────────────────┼──────────────────────────────────────┼─────────────────┤
│ Integration         │ Full stack with Redis and API        │ 29              │
├─────────────────────┼──────────────────────────────────────┼─────────────────┤
│ Security            │ Abuse prevention and attack sim      │ 5               │
├─────────────────────┼──────────────────────────────────────┼─────────────────┤
│ Concurrency         │ Race condition and stress tests      │ 12              │
├─────────────────────┼──────────────────────────────────────┼─────────────────┤
│ TOTAL               │                                      │ 72              │
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
collected 26 items

../tests/unit/test_rate_limit_service.py::test_normalize_email_lowercases PASSED [ 3%]
../tests/unit/test_rate_limit_service.py::test_normalize_email_strips_whitespace PASSED [ 7%]
...

============================== 26 passed in 5.08s ==============================
```

API Endpoints
-------------

### Health Check

```GET /health```

**Response:**

```
{
  "status": "healthy",
  "service": "LeakyBucket",
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
  "service": "Leaky Bucket Rate Limiter",
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
  "algorithm": "Leaky Bucket",
  "default_capacity": "60 water units",
  "default_leak_rate": "1 water unit per second",
  "endpoints": {
    "login": "3 capacity, leak 0.5 per second (IP and Email)",
    "signup": "5 IP / 2 Email capacity, leak 0.2/0.1 per second",
    "default": "60 capacity, leak 1 per second"
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
  "detail": "Leaky Bucket -> Your IP limit exceeded; please try again later!"
}
```

Redis Integration
-----------------

### Redis Key Structure

```
┌──────────────────────────────────────────┬───────────────────────────────────────────────┬───────────────────┬──────────────────┐
│ Key Pattern                              │ Example                                       │ Value             │ TTL              │
├──────────────────────────────────────────┼───────────────────────────────────────────────┼───────────────────┼──────────────────┤
│ rate:{endpoint}:ip:{ip}                  │ rate:login:ip:192.168.1.1                     │ 3:1700000000      │ 3600 seconds     │
├──────────────────────────────────────────┼───────────────────────────────────────────────┼───────────────────┼──────────────────┤
│ rate:{endpoint}:email:{email}            │ rate:login:email:user@test.com                │ 2:1700000000      │ 3600 seconds     │
└──────────────────────────────────────────┴───────────────────────────────────────────────┴───────────────────┴──────────────────┘
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
    
*   **Redis Operations**: Single Lua script per request
    

### Memory Usage

*   **Per Key**: ~50 bytes (counter + key)
    
*   **TTL Strategy**: 1-hour auto-expiry
    
*   **Memory Optimization**: Redis Strings instead of Hashes
    

### Concurrency Safety

*   **Atomic Lua Scripts**: Prevent race conditions
    
*   **Connection Pooling**: Efficient Redis connection reuse
    
*   **Retry Logic**: Automatic retry on timeout
    

### Optimization Tips

1.  ```REDIS_MAX_CONNECTIONS=200```
    
2.  **Use Redis Cluster** for horizontal scaling
    
3. 
```
# High throughput
LeakyBucket(capacity=100.0, leak_rate=10.0)

# Smooth, consistent rate
LeakyBucket(capacity=10.0, leak_rate=0.5)
```
4. ```REDIS_DB=1```
    

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
# 100 capacity, leak 2 per second for API endpoints
API_IP_LIMITER = LeakyBucket(capacity=100.0, leak_rate=2.0)

# 10 capacity, leak 0.1 per second for burst protection
BURST_LIMITER = LeakyBucket(capacity=10.0, leak_rate=0.1)

# 1000 capacity, leak 10 per second for premium users
PREMIUM_LIMITER = LeakyBucket(capacity=1000.0, leak_rate=10.0)
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

### Custom Leaky Bucket Configurations

```
# 5 capacity, leak 0.2 per second (slow leak)
limiter = LeakyBucket(capacity=5.0, leak_rate=0.2)

# 20 capacity, leak 2 per second (fast leak)
limiter = LeakyBucket(capacity=20.0, leak_rate=2.0)

# 100 capacity, leak 10 per second (high throughput)
limiter = LeakyBucket(capacity=100.0, leak_rate=10.0)
```

Monitoring & Observability
--------------------------

### Metrics to Track

*   **Request count**: Total requests processed

*   **Rate limit hits**: 429 responses

*   **Token consumption**: Tokens used per request

*   **Redis latency**: Response time from Redis

*   **Concurrent connections**: Active Redis connections

*   **Token refill rate**: Actual vs configured refill rate

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
    
*   Documentation: [https://github.com/samvelarakelyan00/RateLimiters/tree/main/LeakyBucket](https://github.com/your-username/RateLimiters/tree/main/FixedWindowCounter)

**Documentation Version:** 1.0.0 **Last Updated:** July 2026 **Maintained by:** Samvel Arakelyan