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

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "value": self.value,
            "amount": self.amount,
            "validity_days": self.validity_days,
            "is_used": self.is_used,
        }