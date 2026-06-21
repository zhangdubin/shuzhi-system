"""
合同模块
对应 BACKEND.md §3.2 合同表 + §5.2 状态流转
"""
from datetime import date, datetime
from sqlalchemy import String, Text, Integer, BigInteger, ForeignKey, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class Contract(Base):
    __tablename__ = "contracts"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)  # sales/purchase/service/framework
    client_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("clients.id"), nullable=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id"), nullable=True)
    manager_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    amount: Mapped[int] = mapped_column(BigInteger, default=0)  # 分
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    sign_date: Mapped[date] = mapped_column(Date, nullable=True)
    effective_date: Mapped[date] = mapped_column(Date, nullable=True)
    expire_date: Mapped[date] = mapped_column(Date, nullable=True)
    payment_method: Mapped[str] = mapped_column(String(32), nullable=True)
    payment_term: Mapped[str] = mapped_column(String(32), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)  # draft/approving/approved/signed/executed/expired/archived
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    terms: Mapped[dict] = mapped_column(JSONB, nullable=True)  # [{id, title, content}]
    party_a_signed: Mapped[bool] = mapped_column(default=False)
    party_b_signed: Mapped[bool] = mapped_column(default=False)
    party_a_signed_at: Mapped[datetime] = mapped_column(nullable=True)
    party_b_signed_at: Mapped[datetime] = mapped_column(nullable=True)
    file_id: Mapped[str] = mapped_column(String(32), nullable=True)  # 合同主文件
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系（service 用了 selectinload 这些）
    client: Mapped["Client"] = relationship(foreign_keys=[client_id])
    project: Mapped["Project"] = relationship(foreign_keys=[project_id])
    manager: Mapped["User"] = relationship(foreign_keys=[manager_id])
    creator: Mapped["User"] = relationship(foreign_keys=[created_by])


class ContractTemplate(Base):
    """合同模板（用于起草合同时选用）"""
    __tablename__ = "contract_templates"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)  # sales/purchase/service/framework
    content: Mapped[dict] = mapped_column(JSONB, nullable=True)  # terms 模板
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
