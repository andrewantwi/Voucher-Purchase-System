from typing import List

from fastapi.params import Depends
from loguru import logger
import fastapi

from controller.auth import get_current_user
from controller.user import UserController
from models import User
from schemas.user import UserOut, UserIn, UserUpdate

user_router = fastapi.APIRouter(prefix="/users")


@user_router.get("", response_model=List[UserOut])
async def get_users(current_user: User = Depends(get_current_user)):
    logger.info("Router: Getting all users")
    users=  UserController.get_users()
    return users


@user_router.get("/{user_id}", response_model=UserOut)
async def get_user(user_id: int,current_user: User = Depends(get_current_user)):
    logger.info(f"Router: Getting User with ID: {user_id}")

    return UserController.get_user_by_id(user_id)


@user_router.post("", response_model=UserOut)
async def create_user(user: UserIn,current_user: User = Depends(get_current_user)):
    return UserController.create_user(user)


@user_router.put("/{user_id}", response_model=UserOut)
async def update_user(user_id: int, user: UserUpdate,current_user: User = Depends(get_current_user)):
    return UserController.update_user(user_id, user)


@user_router.delete("/{user_id}")
async def delete_user(user_id: int,current_user: User = Depends(get_current_user)):
    return UserController.delete_user(user_id)

