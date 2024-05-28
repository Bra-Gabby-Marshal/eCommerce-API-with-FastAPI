from fastapi import FastAPI, HTTPException, Request, status, Depends
from tortoise.contrib.fastapi import register_tortoise
from models import *
import logging
import jwt
from jose import JWTError, jwt
from re import template
from starlette.requests import Request
from starlette.responses import HTMLResponse
from tortoise import models

# Authentication
# from authentication import get_hashed_password, very_token
from authentication import*
from fastapi.security import(OAuth2PasswordBearer, OAuth2PasswordRequestForm)

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
oath2_scheme = OAuth2PasswordBearer(tokenUrl='token')

# Token
@app.post('/token')
async def genetate_token(request_form: OAuth2PasswordRequestForm = Depends()):
    token = await token_generator(request_form.username, request_form.password)
    return {"access_token": token, "token_type" : "bearer"}

# Getting current user
async def get_current_user(token: str = Depends(oath2_scheme)):
    try:
        payload = jwt.decode(token, config_credential['SECRET'], algorithms=['HS256'])
        user = await User.get(id = payload.get("id")) 
    except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token or expired token",
                headers={"WWW-Authenticate": "Bearer"}
            )
    return await user
    

logging.basicConfig(level=logging.INFO)

# User Login
@app.post("/login")
async def user_login(user: user_pydanticIn = Depends(get_current_user)):
    business = await Business.get(owner = user)

    return {
        "status": "ok",
        "data": 
        {
             "username" : user.username,
             "email": user.email,
             "verified": user.is_verified,
             "joined_date": user.join_date.strftime("%b %d %Y")
        }
    }

     

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

# Creating User
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

# Email verification
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

# Test route
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
