from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserUpdate(BaseModel):
    full_name: str
    username: str
    email: EmailStr
    is_active: Optional[bool] = True
    is_admin: Optional[bool] = False

class UserIn(UserUpdate):
    password: str

class UserOut(UserUpdate):
    id: int

    class Config:
        from_attributes = True


