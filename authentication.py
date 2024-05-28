from passlib.context import CryptContext

pwd_content = CryptContext(schemes=['bcrypt'], deprecated='auto')

def get_hashed_password(password):
    return pwd_content.hash(password)