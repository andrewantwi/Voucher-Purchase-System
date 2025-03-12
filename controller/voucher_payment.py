import hashlib
import hmac
import json
import os

from fastapi.encoders import jsonable_encoder

from utils.session import SessionManager as DBSession
import requests
from dotenv import load_dotenv
from fastapi import HTTPException, status, BackgroundTasks
from loguru import logger
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from models.user import User
from models.voucher import Voucher
from schemas.payment import WebhookResponse
from schemas.voucher import VoucherPurchase, VoucherOut

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

load_dotenv()
PAYSTACK_URL = os.getenv("PAYSTACK_URL")

PAYSTACK_SECRET_KEY = os.getenv("PAYSTACK_SECRET_KEY")


VOUCHER_TYPE_MAPPING = {
    "10 5days": {"amount": 10.0, "validity_days": 5},
    "20 10days": {"amount": 20.0, "validity_days": 10},
    "50 30days": {"amount": 50.0, "validity_days": 30},
}


class VoucherPaymentController:
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
        payment_status = response_data["status"]

        logger.info(f"Payment initialized, URL: {payment_url}, Access Code: {access_code}, Status: {payment_status}")
        return {
            "payment_url": payment_url,
            "access_code": access_code,
            "status": payment_status,
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
        ).first()

        if not voucher:
            logger.warning(f"No available voucher found for amount: {amount}")
            raise HTTPException(status_code=404, detail="No available voucher found")

        # Mark the voucher as used
        voucher.is_used = True
        voucher.user_id = user.id
        db.commit()
        db.refresh(voucher)

        logger.info(f"Voucher {voucher.code} assigned to user {user.username}, amount: {amount}")
        return VoucherOut.from_attributes(voucher)

    @staticmethod
    async def process_charge_success(db: Session, event: dict):
        """Handle charge.success event in the background"""
        data = event["data"]
        amount = data["amount"] / 100
        user_email = data["customer"]["email"]
        reference = data["reference"]

        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            logger.warning(f"User not found for email: {user_email}")
            return

        voucher = db.query(Voucher).filter(
            Voucher.amount == amount,
            Voucher.is_used == False
        ).first()

        if not voucher:
            logger.warning(f"No available voucher found for amount: {amount}")
            return

        voucher.is_used = True
        voucher.user_id = user.id
        voucher.reference = reference
        voucher.purchased_date = data["transaction_date"]
        db.commit()
        db.refresh(voucher)
        logger.info(f"Voucher bought by user with username: {user.username} and amount: {amount}")

    @staticmethod
    def handle_webhook(db: Session, payload: bytes, signature: str) -> WebhookResponse:
        """Handle Paystack webhook events"""
        # Verify signature
        expected_signature = hmac.new(
            PAYSTACK_SECRET_KEY.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, signature):
            logger.warning("Invalid Paystack webhook signature")
            return WebhookResponse(status="success", message="Event received, invalid signature logged")

        # Parse event
        try:
            event = json.loads(payload.decode('utf-8'))
        except json.JSONDecodeError:
            logger.error("Failed to parse webhook payload")
            raise HTTPException(status_code=400, detail="Invalid payload")

        logger.info(f"Received Paystack webhook event: {event['event']}")

        background_tasks = BackgroundTasks()

        if event["event"] == "charge.success":
            background_tasks.add_task(VoucherPaymentController.process_charge_success, db, event)

        return WebhookResponse(status="success", message="Event received")

    @staticmethod
    def get_voucher_by_reference(voucher_reference: str):

        try:
            with DBSession() as db:
                logger.info(f"Controller: Fetching voucher with reference: {voucher_reference}")
                voucher = db.query(Voucher).filter(Voucher.reference == voucher_reference).first()
                if not voucher:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Voucher not found")
                logger.info(f"Controller: Fetched Voucher ==-> {jsonable_encoder(voucher)}")
                return voucher.to_dict()
        except HTTPException as e:
            logger.error(f"Controller: Voucher with reference: {voucher_reference} not found")
            raise e
        except Exception as e:
            logger.error(f"Controller: Error fetching voucher with reference: {voucher_reference}: {str(e)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error fetching voucher")