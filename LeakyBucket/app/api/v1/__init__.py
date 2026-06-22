from fastapi import APIRouter

from api.v1.endpoints.auth import auth_router


v1_router = APIRouter(
    prefix="/v1",
)


v1_router.include_router(auth_router)