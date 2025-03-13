from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserUpdate(BaseModel):
    full_name: str
    username: str
    email: EmailStr
    is_active: Optional[bool] = True
    is_admin: Optional[bool] = False

class UserIn(BaseModel):
    full_name: str
    username: str
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    full_name: str
    username: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


