from pydantic import BaseModel, EmailStr

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class Token(BaseModel):
    user_id: int
    access_token: str
    token_type: str

class UserLogin(BaseModel):
    username: str
    password: str
