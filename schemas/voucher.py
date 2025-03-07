from typing import List

from pydantic import BaseModel

class VoucherUpdate(BaseModel):
    code: str
    value: int
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

    class Config:
        from_attributes = True


class DeleteUsedVouchersResponse(BaseModel):
    message: str
    deleted: List[str] = []