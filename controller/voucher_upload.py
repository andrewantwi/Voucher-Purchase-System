import hashlib
import hmac
import json
import os
import re
from io import BytesIO
from typing import List

import pdfplumber
import requests
from dotenv import load_dotenv
from fastapi import HTTPException, status, UploadFile, BackgroundTasks
from loguru import logger
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from models.user import User
from models.voucher import Voucher
from schemas.payment import WebhookResponse
from schemas.voucher import UploadVouchersResponse
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


class VoucherUploadController:
    @staticmethod
    def _extract_voucher_codes(pdf_contents: bytes) -> List[str]:
        """Extract 6-character voucher codes from PDF content."""
        try:
            with pdfplumber.open(BytesIO(pdf_contents)) as pdf:
                all_text = "".join(page.extract_text() or "" for page in pdf.pages)
                code_pattern = r"(?<=Quota\s+2\s+GB\s+)([a-z0-9]{6})\s+(?=Concurrent\s+devices)"
                codes = re.findall(code_pattern, all_text, re.MULTILINE)
                if not codes:
                    logger.warning("No voucher codes found in PDF")
                    raise HTTPException(status_code=400, detail="No voucher codes found in PDF")
                return list(set(codes))  # Remove duplicates
        except Exception as e:
            logger.error(f"Error extracting codes from PDF: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to process PDF: {str(e)}")

    @staticmethod
    def _process_voucher_type(voucher_type: str) -> tuple[float, int]:
        """Map voucher_type to amount and validity_days."""
        if voucher_type not in VOUCHER_TYPE_MAPPING:
            raise HTTPException(status_code=400,
                                detail=f"Invalid voucher_type. Supported types: {', '.join(VOUCHER_TYPE_MAPPING.keys())}")
        config = VOUCHER_TYPE_MAPPING[voucher_type]
        return config["amount"], config["validity_days"]

    @staticmethod
    def upload_vouchers(
            db: Session,
            file: UploadFile,
            voucher_type: str,
            user: User
    ):
        """Upload and process a PDF file containing voucher codes."""
        logger.info(f"User {user.username} uploading voucher PDF file: {file.filename} with type: {voucher_type}")

        # Check admin access
        if not user.is_admin:
            logger.warning(f"Unauthorized attempt to upload vouchers by {user.username}")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

        # Validate file type
        if not file.filename.endswith('.pdf'):
            logger.warning(f"Invalid file type uploaded: {file.filename}")
            raise HTTPException(status_code=400, detail="Only PDF files (.pdf) are supported")

        # Process voucher type
        amount, validity_days = VoucherUploadController._process_voucher_type(voucher_type)

        try:
            # Read and extract codes
            contents = file.file.read()
            unique_codes = VoucherUploadController._extract_voucher_codes(contents)

            uploaded_count = 0
            failed_count = 0
            failed_codes = []

            # Process each code
            for code in unique_codes:
                try:
                    if db.query(Voucher).filter(Voucher.code == code).first():
                        logger.warning(f"Duplicate voucher code found: {code}")
                        failed_codes.append(code)
                        failed_count += 1
                        continue

                    voucher = Voucher(
                        code=code,
                        amount=amount,
                        validity_days=validity_days,  # Store validity period
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
            logger.error(f"Error processing upload: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to process upload: {str(e)}")
        finally:
            file.file.close()

