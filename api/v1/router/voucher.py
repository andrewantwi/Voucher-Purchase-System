from typing import List
from fastapi import Depends, Request, UploadFile, File
from loguru import logger
import fastapi
from requests import Session
from controller.voucher_crud import VoucherCRUDController
from controller.voucher_payment import VoucherPaymentController
from controller.voucher_upload import VoucherUploadController
from models.user import User
from controller.auth import get_current_user
from models import get_db, Voucher
from schemas.payment import WebhookResponse
from schemas.voucher import VoucherPurchase, VoucherOut, VoucherPurchaseResponse, VoucherUpdate, VoucherIn, \
    DeleteUsedVouchersResponse, UploadVouchersResponse

voucher_router = fastapi.APIRouter(prefix="/voucher")


voucher_crud_controller = VoucherCRUDController()
voucher_payment_controller = VoucherPaymentController()
voucher_upload_controller = VoucherUploadController()

@voucher_router.post("/buy", response_model=VoucherPurchaseResponse)
def initiate_voucher_purchase(
    purchase: VoucherPurchase,
    voucher: Voucher = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Voucher buy endpoint called by for amount: {purchase.amount}")
    result = voucher_payment_controller.buy_voucher(db, purchase, voucher)
    logger.info(f"Voucher purchase initiated for"
                f"")
    return result

@voucher_router.post("/upload-vouchers", response_model=UploadVouchersResponse)
async def upload_vouchers_endpoint(
    file: UploadFile,
    voucher_type: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Endpoint to upload and process voucher PDF files."""
    return voucher_upload_controller.upload_vouchers(db, file, voucher_type, current_user)

@voucher_router.post("/complete/{reference}", response_model=VoucherOut)
def complete_purchase(
    reference: str,
     user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Voucher completion endpoint called by  with reference: {reference}")
    result = voucher_payment_controller.complete_voucher_purchase(db, reference, user)
    logger.info(f"Voucher purchase completed for ")
    return result

@voucher_router.post("/webhook", response_model=WebhookResponse)
async def handle_paystack_webhook(request: Request, db: Session = Depends(get_db)):
    logger.info("Webhook triggered")
    """Handle Paystack webhook events"""
    payload = await request.body()
    signature = request.headers.get("x-paystack-signature")
    response = await voucher_payment_controller.handle_webhook(db, payload, signature)
    return response

@voucher_router.get("/active_voucher/{voucher_reference}", response_model=VoucherOut)
async def get_voucher_by_reference(voucher_reference: str,user: User = Depends(get_current_user)):
    logger.info(f"Router: Getting Voucher with ID: {voucher_reference}")

    return voucher_payment_controller.get_voucher_by_reference(voucher_reference)


@voucher_router.delete("/used", response_model=DeleteUsedVouchersResponse)
def delete_used_vouchers(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete all vouchers where is_used is True"""

    return voucher_crud_controller.delete_used_vouchers(db, user)


@voucher_router.get("", response_model=List[VoucherOut])
async def get_vouchers(user: User = Depends(get_current_user)):
    logger.info("Router: Getting all vouchers")
    vouchers=  voucher_crud_controller.get_vouchers(user)
    return vouchers

@voucher_router.get("/all_vouchers", response_model=List[VoucherOut])
async def get_vouchers_by_user_id(user: User = Depends(get_current_user)):
    logger.info(f"Router: Getting all vouchers bought by user with id : {user.id}")
    vouchers=  voucher_crud_controller.get_vouchers_by_user_id(user)
    return vouchers


@voucher_router.get("/{voucher_id}", response_model=VoucherOut)
async def get_voucher(voucher_id: int ,user: User = Depends(get_current_user)):
    logger.info(f"Router: Getting Voucher with ID: {voucher_id}")

    return voucher_crud_controller.get_voucher_by_id(voucher_id)


@voucher_router.post("", response_model=VoucherOut)
async def create_voucher(voucher: VoucherIn, user: User = Depends(get_current_user)):
    return voucher_crud_controller.create_voucher(voucher,user)


@voucher_router.put("/{voucher_id}", response_model=VoucherOut)
async def update_voucher(voucher_id: int, voucher: VoucherUpdate, user: User = Depends(get_current_user)):
    return voucher_crud_controller.update_voucher(voucher_id, voucher,user)


@voucher_router.delete("/{voucher_id}")
async def delete_voucher(voucher_id: int, user: User = Depends(get_current_user)):
    return voucher_crud_controller.delete_voucher(voucher_id,user)