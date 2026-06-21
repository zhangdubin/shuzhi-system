"""
发票模板模块
对应 BACKEND.md §3.3 invoice_templates / invoice_template_fields
"""
from datetime import datetime
from sqlalchemy import String, Text, Integer, BigInteger, ForeignKey, Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class InvoiceTemplate(Base):
    __tablename__ = "invoice_templates"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    icon: Mapped[str] = mapped_column(String(8), nullable=True)
    icon_colors: Mapped[str] = mapped_column(String(64), nullable=True)  # "#4F6BFF,#7C3AED"
    default_tax_rate: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_market: Mapped[bool] = mapped_column(Boolean, default=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), default=5.0)
    status: Mapped[str] = mapped_column(String(16), default="enabled", index=True)  # enabled/disabled
    creator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    creator: Mapped["User"] = relationship(foreign_keys=[creator_id])
    fields: Mapped[list["InvoiceTemplateField"]] = relationship(back_populates="template", cascade="all, delete-orphan")


class InvoiceTemplateField(Base):
    """模板字段定义（JSONB 存，灵活）"""
    __tablename__ = "invoice_template_fields"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    template_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("invoice_templates.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    key: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[str] = mapped_column(String(16), nullable=False)  # text/date/amount/rate/user/ref/textarea
    is_required: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_support: Mapped[bool] = mapped_column(Boolean, default=True)
    default_value: Mapped[str] = mapped_column(Text, nullable=True)
    linked_field: Mapped[str] = mapped_column(String(64), nullable=True)
    ref_type: Mapped[str] = mapped_column(String(32), nullable=True)
    options: Mapped[dict] = mapped_column(JSONB, nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    template: Mapped["InvoiceTemplate"] = relationship(back_populates="fields")
