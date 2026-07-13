# Standard libs
from typing import Annotated

# Non-Standard libs
from fastapi import (
    status,
    Depends,
    APIRouter
)

# Own Modules
# Services
from services.auth import AuthService
# Schemas
from schemas.user_schemas import (
    UserCreateSchema,
    UserLoginSchema
)
# Dependencies
from api.dependencies.auth_deps.auth_deps import get_auth_service
from api.dependencies.auth_deps.auth_rate_limiters_dep import (
    get_signup_rate_limiter,
    get_login_rate_limiter
)


auth_router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@auth_router.post("/signup",
                  status_code=status.HTTP_201_CREATED)
async def signup(
        user_signup_data: UserCreateSchema,
        auth_service: Annotated[AuthService, Depends(get_auth_service, use_cache=False)],
        _: Annotated[None, Depends(get_signup_rate_limiter)]
) -> dict:

    result = await auth_service.signup(user_signup_data)

    return result


@auth_router.post("/login")
async def login(
        user_login_data: UserLoginSchema,
        auth_service: Annotated[AuthService, Depends(get_auth_service, use_cache=False)],
        _: Annotated[None, Depends(get_login_rate_limiter)]
) -> dict:

    result = await auth_service.login(user_login_data)

    return result
