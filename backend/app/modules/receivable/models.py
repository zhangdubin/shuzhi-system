"""
回款模块
对应 BACKEND.md §3.4
"""
from datetime import date, datetime
from sqlalchemy import String, Text, Integer, BigInteger, ForeignKey, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class Receivable(Base):
    """回款"""
    __tablename__ = "receivables"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    contract_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("contracts.id"), nullable=True, index=True)
    client_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("clients.id"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=True)  # 合同尾款/预付款/进度款
    plan_amount: Mapped[int] = mapped_column(BigInteger, default=0)  # 分
    received_amount: Mapped[int] = mapped_column(BigInteger, default=0)  # 分
    plan_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    actual_date: Mapped[date] = mapped_column(Date, nullable=True)
    term_days: Mapped[int] = mapped_column(Integer, default=30)
    manager_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    bank_account: Mapped[str] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="pending", index=True)  # pending/partial/completed/overdue/cancelled
    overdue_days: Mapped[int] = mapped_column(Integer, default=0)
    remark: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    client: Mapped["Client"] = relationship(foreign_keys=[client_id])
    contract: Mapped["Contract"] = relationship(foreign_keys=[contract_id])
    manager: Mapped["User"] = relationship(foreign_keys=[manager_id])
    payments: Mapped[list["ReceivablePayment"]] = relationship(back_populates="receivable", cascade="all, delete-orphan")
    reminds: Mapped[list["ReceivableRemind"]] = relationship(back_populates="receivable", cascade="all, delete-orphan")


class ReceivablePayment(Base):
    """到账记录"""
    __tablename__ = "receivable_payments"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    receivable_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("receivables.id", ondelete="CASCADE"), index=True)
    amount: Mapped[int] = mapped_column(BigInteger, default=0)  # 分
    received_at: Mapped[date] = mapped_column(Date, nullable=False)
    bank_statement: Mapped[str] = mapped_column(String(256), nullable=True)  # 凭证 fileId
    remark: Mapped[str] = mapped_column(Text, nullable=True)
    operator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    receivable: Mapped["Receivable"] = relationship(back_populates="payments")


class ReceivableRemind(Base):
    """催收记录"""
    __tablename__ = "receivable_reminds"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    receivable_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("receivables.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)  # phone/email/wechat/letter
    contact_person: Mapped[str] = mapped_column(String(64), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    attachments: Mapped[dict] = mapped_column(JSONB, nullable=True)  # fileId 列表
    operator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    receivable: Mapped["Receivable"] = relationship(back_populates="reminds")
