# Non-Standard libs
from fastapi import FastAPI

# Own Modules
from api.v1 import v1_router


app = FastAPI()


@app.get("/")
async def root():
    return {"message": "Hello World"}


app.include_router(v1_router, prefix="/api")
