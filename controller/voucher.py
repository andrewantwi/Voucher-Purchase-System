import hmac
import hashlib
import re

import pdfplumber
from loguru import logger
from fastapi import HTTPException, status, UploadFile
from sqlalchemy.exc import SQLAlchemyError

from models.voucher import Voucher
from schemas.payment import WebhookResponse
from schemas.voucher import VoucherIn, VoucherUpdate, UploadVouchersResponse
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
import pandas as pd
from io import BytesIO

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
            "amount": int(amount * 100),  # Convert to cedis
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
        return payment_data

    def complete_voucher_purchase(self, db: Session, reference: str, user: User) -> VoucherOut:
        logger.info(f"Completing voucher purchase for user {user.username}, reference: {reference}")

        # Verify payment
        payment_data = self.verify_payment(reference)
        amount = payment_data["amount"] / 100  # Convert to cedis

        # Query an unused voucher that matches the amount
        voucher = db.query(Voucher).filter(
            Voucher.amount == amount,
            Voucher.is_used == False  # Ensure it's not used
        ).first()  # Get the first available voucher

        if not voucher:
            logger.warning(f"No available voucher found for amount: {amount}")
            raise HTTPException(status_code=404, detail="No available voucher found")

        # Mark the voucher as used
        voucher.is_used = True
        db.commit()
        db.refresh(voucher)

        logger.info(f"Voucher {voucher.code} assigned to user {user.username}, amount: {amount}")

        # Return the voucher details
        return VoucherOut.from_attributes(voucher)

    @staticmethod
    def handle_webhook(self, db: Session, payload: bytes, signature: str) -> WebhookResponse:
        """Handle Paystack webhook events"""
        # Verify signature
        expected_signature = hmac.new(
            self.PAYSTACK_SECRET_KEY.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, signature):
            logger.warning("Invalid Paystack webhook signature")
            raise HTTPException(status_code=400, detail="Invalid signature")

        # Parse event
        event = eval(payload.decode('utf-8'))  # Use json.loads in production
        logger.info(f"Received Paystack webhook event: {event['event']}")

        if event["event"] == "charge.success":
            data = event["data"]
            amount = data["amount"] / 100  # Convert from kobo to GHS
            user_email = data["customer"]["email"]
            reference = data["reference"]

            # Find user
            user = db.query(User).filter(User.email == user_email).first()
            if not user:
                logger.warning(f"User not found for email: {user_email}")
                raise HTTPException(status_code=404, detail="User not found")


            logger.info(f"VoucherGHANA created for user {user.username}, amount: {amount}")
            return WebhookResponse(status="success", message="Payment verified and voucher created")

        # Acknowledge other events
        return WebhookResponse(status="success", message="Event received")

    @staticmethod
    def upload_vouchers(self, db: Session, file: UploadFile, user: User,amount: float):
        """Upload and process a PDF file containing voucher codes from Rujie Cloud"""
        logger.info(f"User {user.username} uploading voucher PDF file: {file.filename}")
        if not user.is_admin:
            logger.warning(f"Unauthorized attempt to upload vouchers by {user.username}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        if not file.filename.endswith('.pdf'):
            logger.warning(f"Invalid file type uploaded: {file.filename}")
            raise HTTPException(status_code=400, detail="Only PDF files (.pdf) are supported")

        try:
            contents = file.file.read()
            uploaded_count = 0
            failed_count = 0
            failed_codes = []

            with pdfplumber.open(BytesIO(contents)) as pdf:
                all_text = ""
                for page in pdf.pages:
                    all_text += page.extract_text() or ""

                # Extract codes between profile blocks and concurrent devices
                # Pattern: 6-character alphanumeric codes
                code_pattern = r"(?<=Quota\s+2\s+GB\s+)([a-z0-9]{6})\s+(?=Concurrent\s+devices)"
                codes = re.findall(code_pattern, all_text, re.MULTILINE)

                if not codes:
                    logger.warning("No voucher codes found in PDF")
                    raise HTTPException(status_code=400, detail="No voucher codes found in PDF")

                # Remove duplicates from the list
                unique_codes = list(set(codes))
                logger.info(f"Found {len(unique_codes)} unique voucher codes in PDF")

                for code in unique_codes:
                    try:
                        if db.query(Voucher).filter(Voucher.code == code).first():
                            logger.warning(f"Duplicate voucher code found: {code}")
                            failed_codes.append(code)
                            failed_count += 1
                            continue

                        # Map Quota 2 GB to amount=2.0, user_id defaults to uploader
                        voucher = Voucher(
                            code=code,
                            amount=amount,  # From Quota 2 GB
                            user_id=user.id,
                            is_used=False
                        )
                        db.add(voucher)
                        uploaded_count += 1
                    except Exception as e:
                        logger.error(f"Failed to add voucher {code}: {str(e)}")
                        failed_codes.append(code)
                        failed_count += 1

            db.commit()
            logger.info(f"Uploaded {uploaded_count} vouchers, {failed_count} failed by {user.username}")
            return UploadVouchersResponse(
                message=f"Processed {uploaded_count + failed_count} vouchers",
                uploaded_count=uploaded_count,
                failed_count=failed_count,
                failed_codes=failed_codes
            )

        except Exception as e:
            logger.error(f"Error processing PDF file: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to process PDF file: {str(e)}")
        finally:
            file.file.close()

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
