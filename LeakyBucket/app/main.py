# Standard libs
from contextlib import asynccontextmanager

# Non-Standard libs
from fastapi import FastAPI

# Own Modules
from api.v1 import v1_router
from core.security.rate_limiter.redis_manager import redis_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Server started...")

    # Verify Redis Connection
    try:
        await redis_manager.verify_redis_connection()
        print("Redis connection verified...")
    except Exception as error:
        raise error

    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"Hello": "World"}


app.include_router(v1_router,
                   prefix="/api")