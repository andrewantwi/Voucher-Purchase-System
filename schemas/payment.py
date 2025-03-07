from pydantic import BaseModel

class PaymentRequest(BaseModel):
    value: int

class PaymentResponse(BaseModel):
    payment_url: str
    value: int

class PaymentConfirmation(BaseModel):
    reference: str
    value: int

class VoucherResponse(BaseModel):
    voucher_code: str

class WebhookResponse(BaseModel):
    status: str
    message: str