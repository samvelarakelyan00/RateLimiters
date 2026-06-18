# Standard libs
import os

# Non-Standard libs
from redis.asyncio import Redis


redis_client = Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True
)