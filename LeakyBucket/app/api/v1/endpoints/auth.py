# Standard libs
from typing import Annotated

# Non-Standard libs
from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

# Own Modules
# services
from services.auth import AuthService
# schemas
from schemas.user_schemas import (
    UserCreateSchema,
    UserLoginSchema
)
# dependencies
from api.dependencies.auth_deps.auth_dep import (
    get_auth_service
)

from api.dependencies.auth_deps.auth_rate_limiters_dep import (
    get_signup_rate_limiter,
    get_login_rate_limiter
)


auth_router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@auth_router.post("/signup",
                  status_code=status.HTTP_201_CREATED)
async def signup(
    user_signup_data: UserCreateSchema,
    auth_service: Annotated[AuthService, Depends(get_auth_service, use_cache=False)],
    _: Annotated[None, Depends(get_signup_rate_limiter)]
):

    return await auth_service.signup(
        user_signup_data
    )


@auth_router.post("/login",
                  status_code=status.HTTP_200_OK)
async def login(
    user_login_data: UserLoginSchema,
    auth_service: Annotated[AuthService, Depends(get_auth_service, use_cache=False)],
    _: Annotated[None, Depends(get_login_rate_limiter)]
):

    return await auth_service.login(
        user_login_data
    )


# Test Routers
# @auth_router.get("/dashboard")
# async def get_dashboard(
#     _: Annotated[None, Depends(RateLimitGuard("dashboard", DEFAULT_IP_LIMITER))]
# ):
#     return {"data": "Secure dashboard data"}
#
#
# @auth_router.post("/change-password")
# async def change_password(
#     _: Annotated[None, Depends(RateLimitGuard("change_pwd", DEFAULT_IP_LIMITER, DEFAULT_ACCOUNT_LIMITER))]
# ):
#     return {"message": "Password changed"}
