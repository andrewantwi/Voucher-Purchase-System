from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from schemas.auth import Token
from controller.auth import authenticate_user
from models.database import get_db

auth_router = APIRouter(prefix="/auth", tags=["Auth"])

@auth_router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    return authenticate_user(form_data.username, form_data.password, db)