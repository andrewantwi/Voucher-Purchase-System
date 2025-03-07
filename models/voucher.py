from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, func


from core.setup import Base


class Voucher(Base):
    __tablename__ = "vouchers"
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    value = Column(Integer)
    is_used = Column(Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "value": self.value,
            "is_used": self.is_used,
        }