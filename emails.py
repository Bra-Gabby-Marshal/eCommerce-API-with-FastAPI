from fastapi import (BackgroundTasks, UploadFile, File, Depends, HTTPException, status)
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import BaseModel, EmailStr
from typing import List
from dotenv import dotenv_values
from models import User
import jwt
from jose import JWTError, jwt


class EmailSchema(BaseModel):
    email: List[EmailStr]

# Email credential
config_credentials = dotenv_values(".env")

conf = ConnectionConfig(
    MAIL_USERNAME = config_credentials["EMAIL"],
    MAIL_PASSWORD = config_credentials["PASS"],
    MAIL_FROM = config_credentials["EMAIL"],
    MAIL_PORT = 465,
    MAIL_SERVER = "smtp.gmail.com",
    MAIL_STARTTLS = False,
    MAIL_SSL_TLS = True,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
)

# app = FastAPI()

# @app.post("/email")
async def send_email(email: List, instance: User):

    token_data = {
        "id" : instance.id,
        "username": instance.username
    }

    token = jwt.encode(token_data, config_credentials["SECRET"], algorithm= 'HS256')

    template = f"""
        <!DOCTYPE html>
        <html>
            <head>
            </head>
            <body>
                <div style = "display: flex; align-items: center; justify-content: center; flex-direction: column">
                    <h3>Account Verification</h3>
                    <br>

                    <p>Thanks for choosing EasyShopas, please click on the button below to verify your account</p>
                    
                    <a style="margin-top: 1rem; padding: 1rem; border-radius: 0.5rem; font-size: 1rem; text-decoration: none; background: #0275d8; color:white;"
                    href="http://localhost:8001/verification/?token={token}">Verify your email</a>

                    </p> Please kindly ignore this email if you did not register for EasyShopas and nothing will happend. Thanks</p>
                </div>
            </body>
        </html>
    """
    
    message = MessageSchema(
        subject="EasyShopas Account Verification",
        recipients=email,
        body= template,
        subtype="html")

    fm = FastMail(conf)
    await fm.send_message(message=message)
    # return JSONResponse(status_code=200, content={"message": "email has been sent"})
