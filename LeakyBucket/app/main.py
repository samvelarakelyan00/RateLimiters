# Non-Standard libs
from fastapi import FastAPI

# Own Modules
from api.v1 import v1_router
from core.security.rate_limiter.startup import (
    verify_redis_connection
)


app = FastAPI()


@app.on_event("startup")
async def startup() -> None:
    await verify_redis_connection()


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.include_router(
    v1_router,
    prefix="/api"
)