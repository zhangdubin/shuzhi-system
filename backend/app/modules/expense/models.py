"""
销售费用模块
对应 BACKEND.md §3.3 expenses / expense_breakdowns
（approval_flows / approval_steps 已迁移到 common/models.py，避开循环）
"""
from datetime import date, datetime
from sqlalchemy import String, Text, Integer, BigInteger, ForeignKey, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class Expense(Base):
    __tablename__ = "expenses"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False)  # 差旅/招待/办公/推广/培训/其他
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    amount: Mapped[int] = mapped_column(BigInteger, default=0)  # 分
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    expense_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    applicant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    department_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("departments.id"), nullable=True)
    contract_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("contracts.id"), nullable=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id"), nullable=True)
    cost_center: Mapped[str] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)  # draft/pending/approved/rejected/paid
    submit_at: Mapped[datetime] = mapped_column(nullable=True)
    finish_at: Mapped[datetime] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    applicant: Mapped["User"] = relationship(foreign_keys=[applicant_id])
    department: Mapped["Department"] = relationship(foreign_keys=[department_id])
    breakdowns: Mapped[list["ExpenseBreakdown"]] = relationship(back_populates="expense", cascade="all, delete-orphan")


class ExpenseBreakdown(Base):
    """费用明细拆分（差旅=机票+酒店+打车+餐补）"""
    __tablename__ = "expense_breakdowns"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    expense_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("expenses.id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, default=0)  # 分
    remark: Mapped[str] = mapped_column(Text, nullable=True)
    expense: Mapped["Expense"] = relationship(back_populates="breakdowns")
