from typing import List

from pydantic import BaseModel

class VoucherUpdate(BaseModel):
    amount: float
    code: str
    value: int
    validity_days : int
    is_used: bool

    class Config:
        from_attributes = True


class VoucherPurchaseResponse(BaseModel):
    payment_url: str
    access_code: str
    status: bool
    amount: float



class VoucherPurchase(BaseModel):
    amount: float


class VoucherIn(VoucherUpdate):
    pass

class VoucherOut(VoucherUpdate):
    id: int
    user_id: int

    class Config:
        from_attributes = True


class DeleteUsedVouchersResponse(BaseModel):
    message: str
    deleted: List[str] = []

class UploadVouchersResponse(BaseModel):
    message: str
    uploaded_count: int
    failed_count: int
    failed_codes: list[str]