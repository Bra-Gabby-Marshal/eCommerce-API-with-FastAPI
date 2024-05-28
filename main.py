from fastapi import FastAPI, HTTPException, Request, status
from tortoise.contrib.fastapi import register_tortoise
from models import *
from authentication import get_hashed_password, very_token
import logging
import jwt
from jose import JWTError, jwt
from re import template
from starlette.requests import Request
from starlette.responses import HTMLResponse
from tortoise import models



# signals to create business upon registering user
from tortoise.signals import post_save
from typing import List, Optional, Type
from tortoise import BaseDBAsyncClient
from emails import *

#  Response classes
from fastapi.responses import HTMLResponse

# Template
from fastapi.templating import Jinja2Templates

app = FastAPI()

logging.basicConfig(level=logging.INFO)

# create business upon registering user
@post_save(User)
async def create_business(
    sender: "Type[User]",
    instance: User,
    created: bool,
    using_db: "Optional[BaseDBAsyncClient]",
    updated_fields: List[str]
) -> None:
    if created:
        business_obj = await Business.create(
            business_name=instance.username, owner=instance
        )
        await business_pydantic.from_tortoise_orm(business_obj)
        # sending email
        await send_email([instance.email], instance)

@app.post("/registration")
async def user_registration(user: user_pydanticIn):
    user_info = user.dict(exclude_unset=True)
    logging.info(f"Received user info: {user_info}")

    if "password" not in user_info:
        logging.error("Password field is missing in user info.")
        raise HTTPException(status_code=400, detail="Password field is required.")
    
    user_info["password"] = get_hashed_password(user_info["password"])
    user_obj = await User.create(**user_info)
    new_user = await user_pydanticOut.from_tortoise_orm(user_obj)
    return {
        "status": "ok",
        "data": f"Hello {new_user.username}, thanks for choosing our services. Please check your email inbox to verify your account"
    }

templates = Jinja2Templates(directory="templates")

@app.get("/verification", response_class=HTMLResponse)
async def email_verification(request: Request, token: str):
    user = await very_token(token)
    try:
        if user and not user.is_verified:
            user.is_verified = True
            await user.save()
            return templates.TemplateResponse("verification.html", {"request": request, "username" : user.username})
        
    except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )

@app.get("/")
def index():
    return {"Message": "Welcome to eCommerce API using FastAPI and Tortoise"}

register_tortoise(
    app,
    db_url="sqlite://database.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True
)
