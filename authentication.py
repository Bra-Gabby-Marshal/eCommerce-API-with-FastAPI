from fastapi import HTTPException, status
from passlib.context import CryptContext
import jwt
from jose import JWTError, jwt
from dotenv import dotenv_values
from models import User


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