from loguru import logger
from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from models.voucher import Voucher
from schemas.voucher import VoucherIn, VoucherUpdate
from utils.session import SessionManager as DBSession
from fastapi.encoders import jsonable_encoder
from passlib.context import CryptContext
import requests
from sqlalchemy.orm import Session
from models.user import User
from schemas.voucher import VoucherPurchase, VoucherOut
from datetime import datetime
import os
from dotenv import load_dotenv

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

load_dotenv()
PAYSTACK_URL = os.getenv("PAYSTACK_URL")

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")


class VoucherController:
    def __init__(self):
        self.PAYSTACK_SECRET_KEY = PAYSTACK_SECRET_KEY
        self.VALID_AMOUNTS = [2, 5, 10, 20, 50]
        self.headers = {
            "Authorization": f"Bearer {self.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }

    def initialize_payment(self, amount: float, email: str) -> dict:
        logger.info(f"Initializing payment for amount: {amount}, email: {email}")
        data = {
            "amount": int(amount * 100),  # Convert to kobo
            "email": email,
            "currency": "GHS"
        }
        response = requests.post(f"{PAYSTACK_URL}/initialize",
                                 headers=self.headers, json=data)
        if response.status_code != 200:
            logger.error(f"Payment initialization failed: {response.text}")
            raise HTTPException(status_code=400, detail="Payment initialization failed")

        response_data = response.json()
        payment_url = response_data["data"]["authorization_url"]
        access_code = response_data["data"]["access_code"]
        status = response_data["status"]

        logger.info(f"Payment initialized, URL: {payment_url}, Access Code: {access_code}, Status: {status}")
        return {
            "payment_url": payment_url,
            "access_code": access_code,
            "status": status,
            "amount": amount
        }

    def verify_payment(self, reference: str) -> dict:
        logger.info(f"Verifying payment for reference: {reference}")
        response = requests.get(f"{PAYSTACK_URL}/verify/{reference}",
                                headers=self.headers)
        if response.status_code != 200 or response.json()["data"]["status"] != "success":
            logger.error(f"Payment verification failed: {response.text}")
            raise HTTPException(status_code=400, detail="Payment verification failed")
        logger.info(f"Payment verified successfully for reference: {reference}")
        return response.json()["data"]

    def buy_voucher(self, db: Session, purchase: VoucherPurchase, user: User) -> dict:
        logger.info(f"User {user.username} attempting to buy voucher for {purchase.amount}")
        if purchase.amount not in self.VALID_AMOUNTS:
            logger.warning(f"Invalid amount {purchase.amount} attempted by {user.username}")
            raise HTTPException(status_code=400, detail="Invalid voucher amount. Must be 2, 5, 10, 20, or 50")

        payment_data = self.initialize_payment(purchase.amount, user.email)
        logger.info(f"Voucher purchase initiated for {user.username}, amount: {purchase.amount}")
        return payment_data  # Return the full dict with url, access_code, status, and amount

    def complete_voucher_purchase(self, db: Session, reference: str, user: User) -> VoucherOut:
        logger.info(f"Completing voucher purchase for user {user.username}, reference: {reference}")
        payment_data = self.verify_payment(reference)
        amount = payment_data["amount"] / 100  # Convert back from kobo

        voucher_code = f"VCHR-{user.id}-{int(datetime.now().timestamp())}"
        voucher = Voucher(code=voucher_code, amount=amount, user_id=user.id)
        db.add(voucher)
        db.commit()
        db.refresh(voucher)
        logger.info(f"Voucher {voucher_code} created for user {user.username}, amount: {amount}")
        return VoucherOut.from_attributes(voucher)

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
                hashed_password = pwd_context.hash(voucher.password)

                # Create voucher dictionary with hashed password instead of plain text
                voucher_data = voucher.model_dump()
                voucher_data["hashed_password"] = hashed_password
                del voucher_data["password"]  # Remove plain text password

                voucher_instance = Voucher(**voucher_data)
                logger.info(f"Controller: Creating voucher: {voucher_instance.to_dict()}")
                db.add(voucher_instance)
                db.commit()
                db.refresh(voucher_instance)
                logger.info(f"Controller: Voucher created with ID {voucher_instance.full_name}")

                return voucher_instance.to_dict()
        except SQLAlchemyError as e:
            logger.error(f"Controller: SQLAlchemy Error while creating voucher {voucher.full_name}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Controller: Error creating voucher: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail=f"Error creating voucher: {str(e)}")

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
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error updating voucher: {str(e)}")

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
