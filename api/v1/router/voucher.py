from typing import List

from fastapi import Depends, Request, UploadFile, File
from loguru import logger
import fastapi
from requests import Session
from models.user import User
from controller.auth import get_current_user
from controller.voucher import VoucherController
from models import get_db, Voucher
from schemas.payment import WebhookResponse
from schemas.voucher import VoucherPurchase, VoucherOut, VoucherPurchaseResponse, VoucherUpdate, VoucherIn, \
    DeleteUsedVouchersResponse, UploadVouchersResponse

voucher_router = fastapi.APIRouter(prefix="/voucher")


voucher_controller = VoucherController()

@voucher_router.post("/buy", response_model=VoucherPurchaseResponse)
def initiate_voucher_purchase(
    purchase: VoucherPurchase,
    voucher: Voucher = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Voucher buy endpoint called by for amount: {purchase.amount}")
    result = voucher_controller.buy_voucher(db, purchase, voucher)
    logger.info(f"Voucher purchase initiated for"
                f"")
    return result

@voucher_router.post("/upload/{amount}", response_model=UploadVouchersResponse)
def upload_vouchers(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a PDF file containing voucher codes"""
    return voucher_controller.upload_vouchers(db, file, user)

@voucher_router.post("/complete/{reference}", response_model=VoucherOut)
def complete_purchase(
    reference: str,
    voucher: Voucher = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Voucher completion endpoint called by  with reference: {reference}")
    result = voucher_controller.complete_voucher_purchase(db, reference, voucher)
    logger.info(f"Voucher purchase completed for ")
    return result

@voucher_router.post("/webhook", response_model=WebhookResponse)
async def handle_paystack_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Paystack webhook events"""
    payload = await request.body()
    signature = request.headers.get("x-paystack-signature")
    response = voucher_controller.handle_webhook(db, payload, signature)
    return response


@voucher_router.delete("/used", response_model=DeleteUsedVouchersResponse)
def delete_used_vouchers(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete all vouchers where is_used is True"""

    return voucher_controller.delete_used_vouchers(db, user)


@voucher_router.get("", response_model=List[VoucherOut])
async def get_vouchers():
    logger.info("Router: Getting all vouchers")
    vouchers=  VoucherController.get_vouchers()
    return vouchers


@voucher_router.get("/{voucher_id}", response_model=VoucherOut)
async def get_voucher(voucher_id: int):
    logger.info(f"Router: Getting Voucher with ID: {voucher_id}")

    return VoucherController.get_voucher_by_id(voucher_id)


@voucher_router.post("", response_model=VoucherOut)
async def create_voucher(voucher: VoucherIn):
    return VoucherController.create_voucher(voucher)


@voucher_router.put("/{voucher_id}", response_model=VoucherOut)
async def update_voucher(voucher_id: int, voucher: VoucherUpdate):
    return VoucherController.update_voucher(voucher_id, voucher)


@voucher_router.delete("/{voucher_id}")
async def delete_voucher(voucher_id: int):
    return VoucherController.delete_voucher(voucher_id)