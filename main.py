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

# image upload
from fastapi import File, UploadFile
import secrets
from fastapi.staticfiles import StaticFiles
from PIL import Image

app = FastAPI()

oath2_scheme = OAuth2PasswordBearer(tokenUrl='token')

# static file setup config
app.mount("/static", StaticFiles(directory="static"), name="static")

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
    # profile image in login
    logo = business.logo
    logo_path = "localhost:8001/static/images/"+logo

    return {
        "status": "ok",
        "data": 
        {
             "username" : user.username,
             "email": user.email,
             "verified": user.is_verified,
             "joined_date": user.join_date.strftime("%b %d %Y"),
             "logo": logo_path
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

# Image upload route
@app.post("/uploadfile/profile")
async def create_upload_file(file: UploadFile = File(...), user: user_pydantic = Depends(get_current_user)):
    FILEPATH = "./static/images/"
    filename = file.filename
    extension = filename.split(".")[1]

    if extension not in ["png", "jpg"]:
         return {"status" : "error", "detail" : "File extension not allowed"}

    token_name = secrets.token_hex(10)+"."+extension
    genetated_name = FILEPATH + token_name
    file_content = await file.read() 

    with open(genetated_name, "wb") as file:
         file.write(file_content)

    # Pillow to reduce image size
    img = Image.open(genetated_name)
    img = img.resize(size = (200, 200))
    img.save(genetated_name)

    file.close()

    business = await Business.get(owner = user)
    owner = await business.owner

    if owner == user:
         business.logo = token_name
         await business.save()

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
            )
    
    file_url = "localhost:8001" + genetated_name[1:]
    return {"status" : "ok", "filename": file_url}
         
# Product upload route
@app.post("/uploadfile/product/{id}")
async def create_upload_file( id: int, file: UploadFile = File(...), user: user_pydantic = Depends(get_current_user)):
    FILEPATH = "./static/products/"
    filename = file.filename
    extension = filename.split(".")[1]

    if extension not in ["png", "jpg"]:
         return {"status" : "error", "detail" : "File extension not allowed"}

    token_name = secrets.token_hex(10)+"."+extension
    genetated_name = FILEPATH + token_name
    file_content = await file.read() 

    with open(genetated_name, "wb") as file:
         file.write(file_content)

    # Pillow to reduce image size
    img = Image.open(genetated_name)
    img = img.resize(size = (200, 200))
    img.save(genetated_name)

    file.close()

    product = await Product.get(id = id)
    business = await product.business
    owner = await business.owner

    if owner == user:
        product.product_image = token_name
        await product.save()

    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
            )
    
    file_url = "localhost:8001" + genetated_name[1:]
    return {"status" : "ok", "filename": file_url}
    
# Product CRUD functionalities

# Create Product
@app.post("/products")
async def add_new_product(product: product_pydanticIn, 
                            user: user_pydantic = Depends(get_current_user)):
    product = product.dict(exclude_unset = True)
    # to avoid division by zero error
    if product['original_price'] > 0:
        product["percentage_discount"] = ((product["original_price"] - product['new_price'] ) / product['original_price']) * 100

    product_obj = await Product.create(**product, business = user)
    product_obj = await product_pydantic.from_tortoise_orm(product_obj)
    return {"status" : "ok", "data" : product_obj}


# Get All Products
@app.get("/products")
async def get_products():
    response = await product_pydantic.from_queryset(Product.all())
    return {"status" : "ok", "data" : response}


# Get a specific product
@app.get("/product/{id}")
async def get_product(id: int):
    product = await Product.get(id = id)
    business = await product.business
    owner = await business.owner
    response = await product_pydantic.from_queryset_single(Product.get(id = id))

    return {
         "status": "ok",
         "data": {
              "product_details": response,
              "business_details": {
                   "name": business.business_name,
                   "city": business.city,
                   "region": business.region,
                   "description": business.business_description,
                   "logo": business.logo,
                   "owner_id": owner.id,
                   "email": owner.email,
                   "join_date": owner.join_date.strftime("%b %d %Y")
              }
         }
    }


# Update Product
@app.put("/product/{id}")
async def update_product(id: int, update_info: product_pydanticIn, user: user_pydantic = Depends(get_current_user)):
    product = await Product.get_or_none(id=id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    business = await product.business
    if not business:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")

    owner = await business.owner
    if not owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Owner not found")

    update_info = update_info.dict(exclude_unset=True)
    update_info["date_published"] = datetime.now(timezone.utc)

    if user == owner:
        if "original_price" in update_info and update_info["original_price"] <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Original price must be greater than zero")
        if "new_price" in update_info and update_info["new_price"] < 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New price cannot be negative")

        if update_info["original_price"] != 0:
            update_info["percentage_discount"] = ((update_info["original_price"] - update_info["new_price"]) / update_info["original_price"]) * 100
        
        product = await product.update_from_dict(update_info)
        await product.save()
        response = await product_pydantic.from_tortoise_orm(product)
        return {"status": "ok", "data": response}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action or invalid user input",
            headers={"WWW-Authenticate": "Bearer"}
        )

# Delete a Product
@app.delete("/products/{id}")
async def delete_product(id: int, user: user_pydantic = Depends(get_current_user)):
    try:
        product = await Product.get(id=id).prefetch_related('business', 'business__owner')
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )

    business = product.business
    owner = business.owner

    if user == owner:
        await product.delete()
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return {"status": "ok"}

# Update business details
@app.put("/business/{id}")
async def update_business(id: int, update_business: business_pydanticIn, user: user_pydantic = Depends(get_current_user)):
    update_business = update_business.dict()
    business = await Business.get(id = id)
    business_owner = await business.owner

    if user == business_owner:
        await business.update_from_dict(update_business)
        business.save()
        response = await business_pydantic.from_tortoise_orm(business)
        return {"status": "ok", "data": response}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated to perform this action",
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
