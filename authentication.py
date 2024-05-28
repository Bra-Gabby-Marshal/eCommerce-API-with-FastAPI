from fastapi import HTTPException, status
from passlib.context import CryptContext
import jwt
from jose import JWTError, jwt
from dotenv import dotenv_values
from models import User

# .env
config_credential = dotenv_values(".env")

pwd_content = CryptContext(schemes=['bcrypt'], deprecated='auto')

# Password hashed
def get_hashed_password(password):
    return pwd_content.hash(password)

# verify token
async def very_token(token: str):
    try:
        payload = jwt.decode(token, config_credential["SECRET"], algorithms= ['HS256'])
        user = await User.get(id = payload.get("id"))
    
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user

# Token Generator
async def verify_password(plain_password, hashed_password):
    return pwd_content.verify(plain_password, hashed_password)

async def authenticate_user(username, password):
    user = await User.get(username = username)

    if user and verify_password(password, user.password):
        return user
    return False

async def token_generator(username: str, password: str):
    user = await authenticate_user(username, password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    token_data = {
        "id": user.id,
        "username": user.username
    }

    token = jwt.encode(token_data, config_credential['SECRET'])

    return token
