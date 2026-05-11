from pydantic import BaseModel
from typing import Optional

class LoginSchema(BaseModel):
    email: str
    password: str

class JogoSchema(BaseModel):
    nome: str
    tipo: str
    nota: int
    review: str

    class Config:
        from_attributes = True

class JogoResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    nota: int
    review: str

    class Config:
        from_attributes = True