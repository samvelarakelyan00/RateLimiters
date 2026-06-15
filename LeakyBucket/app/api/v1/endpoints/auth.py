from typing import Annotated

from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

from services.auth import AuthService

from schemas.user_schemas import (
    UserCreateSchema,
    UserLoginSchema,
)

from api.dependencies.auth_dep import (
    get_auth_service,
)

from api.dependencies.auth_rate_limiters import (
    AuthRateLimitGuard,
)

auth_router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)


@auth_router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED
)
async def signup(
    user_signup_data: UserCreateSchema,
    auth_service: Annotated[
        AuthService,
        Depends(get_auth_service)
    ],
    _: Annotated[
        None,
        Depends(AuthRateLimitGuard("signup"))
    ]
):
    return await auth_service.signup(
        user_signup_data
    )


@auth_router.post(
    "/login",
    status_code=status.HTTP_200_OK
)
async def login(
    user_login_data: UserLoginSchema,
    auth_service: Annotated[
        AuthService,
        Depends(get_auth_service)
    ],
    _: Annotated[
        None,
        Depends(AuthRateLimitGuard("login"))
    ]
):
    return await auth_service.login(
        user_login_data
    )