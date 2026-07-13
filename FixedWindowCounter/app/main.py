# Standard libs
import time
from enum import Enum
from typing import Dict, Any
from contextlib import asynccontextmanager

# Non-Standard libs
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

# Own Modules
from api.v1 import v1_router
from core.security.rate_limiter.redis_manager import redis_manager


class ServiceStatus(str, Enum):
    """Service status enumeration."""
    OPERATIONAL = "operational"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"
    UNHEALTHY = "unhealthy"
    INITIALIZING = "initializing"
    SHUTTING_DOWN = "shutting_down"


class ServiceHealth:
    """Service health state manager."""

    def __init__(self):
        self._status = ServiceStatus.INITIALIZING
        self._started_at = time.time()
        self._checks: Dict[str, bool] = {}
        self._details: Dict[str, Any] = {}

    def set_status(self, status: ServiceStatus, details: Dict[str, Any] = None):
        """Update service status."""
        self._status = status
        if details:
            self._details.update(details)

    def get_health(self) -> Dict[str, Any]:
        """Get complete health status."""
        return {
            "status": self._status.value,
            "uptime_seconds": int(time.time() - self._started_at),
            "checks": self._checks,
            "details": self._details
        }


# Global health manager
health = ServiceHealth()


@asynccontextmanager
async def lifespan(app: FastAPI):
    health.set_status(ServiceStatus.INITIALIZING, {"phase": "starting"})

    print("Server started...")

    try:
        await redis_manager.verify_redis_connection()
        print("Redis connection verified...")
        health._checks["redis"] = True
        health.set_status(ServiceStatus.OPERATIONAL, {"redis": "connected"})
    except Exception as error:
        health.set_status(ServiceStatus.UNHEALTHY, {"redis": "failed", "error": str(error)})
        raise error

    yield

    health.set_status(ServiceStatus.SHUTTING_DOWN, {"phase": "shutdown"})
    print("Server shutting down...")
    await redis_manager.client.aclose()


app = FastAPI(
    title="Fixed Window Counter Rate Limiter",
    description="A high-performance, distributed Fixed Window Counter rate limiter",
    version="0.1.0",
    lifespan=lifespan
)


# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Public"])
async def read_root():
    """Public informational endpoint."""
    return {
        "service": "Fixed Window Counter Rate Limiter",
        "version": "0.1.0",
        "status": health._status.value,  # Dynamic status
        "uptime_seconds": int(time.time() - health._started_at)
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Detailed health check endpoint.
    Verifies Redis connectivity and service health.
    """
    health_status = {
        "status": "healthy",
        "service": "FixedWindowCounter",
        "version": "0.1.0",
        "timestamp": time.time(),
        "checks": {
            "redis": False
        }
    }

    # Check Redis connectivity
    try:
        await redis_manager.verify_redis_connection()
        health_status["checks"]["redis"] = True
    except Exception:
        health_status["status"] = "unhealthy"
        health_status["checks"]["redis"] = False

    return JSONResponse(
        status_code=200 if health._status != ServiceStatus.UNHEALTHY else 503,
        content=health_status
    )


@app.get("/rate-limit-info", tags=["Public"])
async def rate_limit_info():
    """Information about current rate limiting configuration."""
    return {
        "algorithm": "Fixed Window Counter",
        "default_window_size": "60 seconds",
        "default_limit": "60 requests per window",
        "endpoints": {
            "login": "3 attempts per 60 seconds (IP and Email)",
            "signup": "5 attempts per 60 seconds (IP), 2 per 60 seconds (Email)",
            "default": "60 requests per 60 seconds"
        }
    }


app.include_router(v1_router,
                   prefix="/api")