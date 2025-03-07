from typing import Optional
from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.orm import Session
from models import User
from passlib.context import CryptContext
from jose import jwt, JWTError
from dotenv import load_dotenv
import os
from utils.session import SessionManager as DBSession  # Assuming this is your session manager

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

class TokenData(BaseModel):
    user_id: Optional[int] = None  # Optional[int] allows None or int

def authenticate_user(username: str, password: str, db: Session):
    logger.info(f"Authenticating user with email: {username}")
    user = db.query(User).filter(User.username == username).first()
    if not user or not pwd_context.verify(password, user.hashed_password):
        logger.warning(f"Authentication failed for email: {username}")
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = jwt.encode({"sub": str(user.id)}, SECRET_KEY, algorithm=ALGORITHM)  # Use user.id
    logger.info(f"Access token generated for user: {user.username}")
    return {"access_token": access_token,"user_id": user.id, "token_type": "bearer"}

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    logger.info(f"Validating token: {token[:10]}...")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception
        user_id = int(user_id_str)  # Convert to int
        token_data = TokenData(user_id=user_id)
        logger.debug(f"Token decoded, user_id: {user_id}")
    except ValueError:
        logger.error(f"Invalid user_id in token: {user_id_str}")
        raise credentials_exception
    except JWTError as e:
        logger.error(f"JWT validation failed: {str(e)}")
        raise credentials_exception

    with DBSession() as db:
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if user is None or not user.is_active:
            logger.warning(f"User not found or inactive: {token_data.user_id}")
            raise credentials_exception
        logger.info(f"User authenticated: {user.username}")
        return user