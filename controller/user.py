from loguru import logger
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from models.user import User
from schemas.user import UserIn, UserUpdate
from utils.session import SessionManager as DBSession
from fastapi.encoders import jsonable_encoder
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserController:

    @staticmethod
    def get_users():
        try:
            with DBSession() as db:
                logger.info("Controller: Fetching all users")
                users = db.query(User).all()
                users_list = [user.to_dict() for user in users]
                logger.info(f"Controller: Fetched Users ==-> {users_list}")
                return users_list
        except Exception as e:
            logger.error(f"Controller: Error fetching users: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching users")

    @staticmethod
    def get_user_by_id(user_id: int):
        try:
            with DBSession() as db:
                logger.info(f"Controller: Fetching user with ID {user_id}")
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
                logger.info(f"Controller: Fetched User ==-> {jsonable_encoder(user)}")
                return user.to_dict()
        except HTTPException as e:
            logger.error(f"Controller: User with ID {user_id} not found")
            raise e
        except Exception as e:
            logger.error(f"Controller: Error fetching user with ID {user_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching user")

    @staticmethod
    def create_user(user: UserIn):
        try:
            with DBSession() as db:
                logger.info(f"Controller: Creating user: {user.full_name}")
                existing_user = db.query(User).filter(User.username == user.username).first()
                if existing_user:
                    raise HTTPException(status_code=400, detail="User with this email or username already exists")
                hashed_password = pwd_context.hash(user.password)

                # Create user dictionary with hashed password instead of plain text
                user_data = user.model_dump()
                user_data["hashed_password"] = hashed_password
                del user_data["password"]  # Remove plain text password

                user_instance = User(**user_data)
                logger.info(f"Controller: Creating user: {user_instance.to_dict()}")
                db.add(user_instance)
                db.commit()
                db.refresh(user_instance)
                logger.info(f"Controller: User created with ID {user_instance.full_name}")

                return user_instance.to_dict()
        except SQLAlchemyError as e:
            logger.error(f"Controller: SQLAlchemy Error while creating user {user.full_name}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Controller: Error creating user: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Error creating user: {str(e)}")

    @staticmethod
    def update_user(user_id: int, update_data: UserUpdate):
        try:
            with DBSession() as db:
                logger.info(f"Controller: Updating user with ID {user_id}")
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User not found")

                for key, value in update_data.model_dump(exclude_unset=True).items():
                    setattr(user, key, value)
                db.commit()
                db.refresh(user)
                logger.info(f"Controller: User with ID {user_id} updated")
                return user.to_dict()

        except SQLAlchemyError as e:
            logger.error(f"Controller: SQLAlchemy Error while updating user with ID {user_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Controller: Error updating user with ID {user_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error updating user: {str(e)}")

    @staticmethod
    def delete_user(user_id: int):
        with DBSession() as db:
            logger.info(f"Controller: Deleting user with ID {user_id}")
            user = db.query(User).filter(User.id == user_id).first()

            if not user:
                logger.error(f"Controller: User with ID {user_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with ID {user_id} not found"
                )

            try:
                db.delete(user)
                db.commit()
                logger.info(f"Controller: User with ID {user_id} deleted")
                return {"message": f"User with ID {user_id} deleted successfully"}
            except SQLAlchemyError as e:
                db.rollback()  # Rollback transaction in case of error
                logger.error(f"Controller: SQLAlchemy Error while deleting user with ID {user_id}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error:{str(e)}"
                )
            except Exception as e:
                db.rollback()
                logger.error(f"Controller: Unexpected error deleting user with ID {user_id}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error deleting user"
                )

