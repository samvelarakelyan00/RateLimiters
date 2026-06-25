# Own Modules
from schemas.user_schemas import (
    UserCreateSchema,
    UserLoginSchema
)


class AuthService:
    def __init__(self) -> None:
        pass

    async def signup(self, user_signup_data: UserCreateSchema) -> dict:
        return {"message": f"{self.__class__} | User signup was successful"}

    async def login(self, user_login_data: UserLoginSchema) -> dict:
        return {"message": f"{self.__class__} | User login was successful"}
