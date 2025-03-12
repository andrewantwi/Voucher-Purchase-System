from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.user import User
from models.voucher import Voucher
from schemas.voucher import VoucherIn, VoucherUpdate
from utils.session import SessionManager as DBSession


class VoucherCRUDController:

    @staticmethod
    def get_vouchers():
        try:
            with DBSession() as db:
                logger.info("Controller: Fetching all vouchers")
                vouchers = db.query(Voucher).all()
                vouchers_list = [voucher.to_dict() for voucher in vouchers]
                logger.info(f"Controller: Fetched Vouchers ==-> {vouchers_list}")
                return vouchers_list
        except Exception as e:
            logger.error(f"Controller: Error fetching vouchers: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching vouchers")

    @staticmethod
    def get_vouchers_by_user_id(user_id: int):
        try:
            with DBSession() as db:
                logger.info("Controller: Fetching all vouchers by user ID")
                vouchers = db.query(Voucher).filter(Voucher.user_id == user_id).all()
                vouchers_list = [voucher.to_dict() for voucher in vouchers]
                logger.info(f"Controller: Fetched Vouchers ==-> {vouchers_list}")
                return vouchers_list
        except Exception as e:
            logger.error(f"Controller: Error fetching vouchers: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching vouchers")

    @staticmethod
    def get_voucher_by_id(voucher_id: int):

        try:
            with DBSession() as db:
                logger.info(f"Controller: Fetching voucher with ID {voucher_id}")
                voucher = db.query(Voucher).filter(Voucher.id == voucher_id).first()
                if not voucher:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voucher not found")
                logger.info(f"Controller: Fetched Voucher ==-> {jsonable_encoder(voucher)}")
                return voucher.to_dict()
        except HTTPException as e:
            logger.error(f"Controller: Voucher with ID {voucher_id} not found")
            raise e
        except Exception as e:
            logger.error(f"Controller: Error fetching voucher with ID {voucher_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching voucher")


    @staticmethod
    def create_voucher(voucher: VoucherIn):
        try:
            with DBSession() as db:
                # Check if the voucher code already exists
                existing_voucher = db.query(Voucher).filter(Voucher.code == voucher.code).first()
                if existing_voucher:
                    raise HTTPException(status_code=400, detail="Voucher code already exists!")

                # Convert Pydantic model to dictionary
                voucher_data = voucher.model_dump()

                # Create and save the voucher instance
                voucher_instance = Voucher(**voucher_data)
                logger.info(f"Controller: Creating voucher: {voucher_instance.to_dict()}")

                db.add(voucher_instance)
                db.commit()
                db.refresh(voucher_instance)

                logger.info(f"Controller: Voucher created with code {voucher_instance.code}")

                return voucher_instance.to_dict()

        except SQLAlchemyError as e:
            logger.error(f"Controller: SQLAlchemy Error while creating voucher: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )

        except Exception as e:
            logger.error(f"Controller: Error creating voucher: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error creating voucher: {str(e)}"
            )

    @staticmethod
    def update_voucher(voucher_id: int, update_data: VoucherUpdate):
        try:
            with DBSession() as db:
                logger.info(f"Controller: Updating voucher with ID {voucher_id}")
                voucher = db.query(Voucher).filter(Voucher.id == voucher_id).first()
                if not voucher:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Voucher not found")

                for key, value in update_data.model_dump(exclude_unset=True).items():
                    setattr(voucher, key, value)
                db.commit()
                db.refresh(voucher)
                logger.info(f"Controller: Voucher with ID {voucher_id} updated")
                return voucher.to_dict()

        except SQLAlchemyError as e:
            logger.error(f"Controller: SQLAlchemy Error while updating voucher with ID {voucher_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Controller: Error updating voucher with ID {voucher_id}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Error updating voucher: {str(e)}")

    @staticmethod
    def delete_voucher(voucher_id: int):
        with DBSession() as db:
            logger.info(f"Controller: Deleting voucher with ID {voucher_id}")
            voucher = db.query(Voucher).filter(Voucher.id == voucher_id).first()

            if not voucher:
                logger.error(f"Controller: Voucher with ID {voucher_id} not found")
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Voucher with ID {voucher_id} not found"
                )

            try:
                db.delete(voucher)
                db.commit()
                logger.info(f"Controller: Voucher with ID {voucher_id} deleted")
                return {"message": f"Voucher with ID {voucher_id} deleted successfully"}
            except SQLAlchemyError as e:
                db.rollback()  # Rollback transaction in case of error
                logger.error(f"Controller: SQLAlchemy Error while deleting voucher with ID {voucher_id}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Database error:{str(e)}"
                )
            except Exception as e:
                db.rollback()
                logger.error(f"Controller: Unexpected error deleting voucher with ID {voucher_id}: {str(e)}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error deleting voucher"
                )

    @staticmethod
    def delete_used_vouchers(self, db: Session, user: User) -> dict:
        """Delete all vouchers where is_used is True"""
        logger.info(f"User {user.username} requested deletion of used vouchers")
        if not user.is_admin:  # Restrict to admins
            logger.warning(f"Unauthorized attempt to delete used vouchers by {user.username}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        # Delete used vouchers in one query
        deleted_count = db.query(Voucher).filter(Voucher.is_used == True).delete(synchronize_session=False)
        db.commit()

        if deleted_count == 0:
            logger.info("No used vouchers found to delete")
            return {"message": "No used vouchers found", "deleted_count": 0}

        logger.info(f"Deleted {deleted_count} used vouchers by {user.username}")
        return {"message": f"Deleted {deleted_count} used vouchers", "deleted_count": deleted_count}
