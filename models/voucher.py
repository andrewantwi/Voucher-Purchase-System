from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func, Float

from core.setup import Base


class Voucher(Base):
    __tablename__ = "vouchers"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    amount = Column(Float)
    value = Column(Integer)
    validity_days = Column(Integer)
    is_used = Column(Boolean, default=False)
    purchased_date = Column(DateTime,nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    reference = Column(String, unique=True, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "value": self.value,
            "amount": self.amount,
            "validity_days": self.validity_days,
            "purchased_date": self.purchased_date,
            "reference": self.reference,
            "user_id": self.user_id,
            "is_used": self.is_used,
        }