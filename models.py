from tortoise import Model, fields
from pydantic import BaseModel


class User(Model):
    id = fil