"""
发票识别模块
对应 BACKEND.md §3.3 invoices / invoice_relations / invoice_batch_tasks / invoice_batch_items
"""
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import String, Text, Integer, BigInteger, ForeignKey, Boolean, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    invoice_type: Mapped[str] = mapped_column(String(32), nullable=False)
    invoice_code: Mapped[str] = mapped_column(String(32), nullable=True, index=True)
    invoice_no: Mapped[str] = mapped_column(String(32), nullable=True, index=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=True, index=True)
    seller_name: Mapped[str] = mapped_column(String(128), nullable=True)
    seller_tax_no: Mapped[str] = mapped_column(String(32), nullable=True)
    buyer_name: Mapped[str] = mapped_column(String(128), nullable=True)
    buyer_tax_no: Mapped[str] = mapped_column(String(32), nullable=True)
    total_amount: Mapped[int] = mapped_column(BigInteger, default=0)  # 分
    total_amount_cn: Mapped[str] = mapped_column(String(64), nullable=True)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    tax_amount: Mapped[int] = mapped_column(BigInteger, default=0)
    amount_excl_tax: Mapped[int] = mapped_column(BigInteger, default=0)
    confidence: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    verify_status: Mapped[str] = mapped_column(String(16), default="pending")  # pending/verified/failed/expired
    verify_at: Mapped[datetime] = mapped_column(nullable=True)
    verify_source: Mapped[str] = mapped_column(String(32), nullable=True)
    verify_code: Mapped[str] = mapped_column(String(64), nullable=True)  # 校验码（电子发票 20 位）
    remarks: Mapped[str] = mapped_column(String(512), nullable=True)  # 备注
    file_url: Mapped[str] = mapped_column(String(256), nullable=True)
    file_id: Mapped[str] = mapped_column(String(32), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)
    items: Mapped[dict] = mapped_column(JSONB, nullable=True)  # 商品明细
    raw_ocr: Mapped[dict] = mapped_column(JSONB, nullable=True)  # 原始 OCR
    status: Mapped[str] = mapped_column(String(16), default="uploaded", index=True)
    # uploaded/recognized/pending_verify/verified/submitted/archived/rejected
    is_linked_contract: Mapped[bool] = mapped_column(Boolean, default=False)
    is_linked_project: Mapped[bool] = mapped_column(Boolean, default=False)
    uploader_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True, index=True)
    uploaded_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class InvoiceRelation(Base):
    """发票关联（多对多）"""
    __tablename__ = "invoice_relations"
    invoice_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("invoices.id", ondelete="CASCADE"), primary_key=True)
    relation_type: Mapped[str] = mapped_column(String(16), primary_key=True)  # contract/project/expense/receivable
    relation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)


class InvoiceBatchTask(Base):
    """批量识别任务（SSE 推送）"""
    __tablename__ = "invoice_batch_tasks"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    template_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    total: Mapped[int] = mapped_column(Integer, default=0)
    uploading: Mapped[int] = mapped_column(Integer, default=0)
    recognizing: Mapped[int] = mapped_column(Integer, default=0)
    success: Mapped[int] = mapped_column(Integer, default=0)
    warning: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(16), default="processing", index=True)  # processing/done/error
    uploader_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    finished_at: Mapped[datetime] = mapped_column(nullable=True)


class InvoiceBatchItem(Base):
    """批量任务文件项"""
    __tablename__ = "invoice_batch_items"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    batch_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("invoice_batch_tasks.id", ondelete="CASCADE"), index=True)
    file_id: Mapped[str] = mapped_column(String(64), nullable=False)
    filename: Mapped[str] = mapped_column(String(256), nullable=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=True)
    file_url: Mapped[str] = mapped_column(String(256), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    # queued/uploading/recognizing/success/warning/failed
    progress: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=0)
    invoice_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("invoices.id"), nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(nullable=True)
    finished_at: Mapped[datetime] = mapped_column(nullable=True)


class InvoiceVerifyRecord(Base):
    """发票查验记录"""
    __tablename__ = "invoice_verify_records"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    invoice_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("invoices.id"), nullable=True, index=True)
    invoice_code: Mapped[str] = mapped_column(String(32), nullable=True)
    invoice_no: Mapped[str] = mapped_column(String(32), nullable=True)
    issue_date: Mapped[date] = mapped_column(Date, nullable=True)
    total_amount: Mapped[int] = mapped_column(BigInteger, nullable=True)  # 分
    result: Mapped[str] = mapped_column(String(16), nullable=False)  # pass/repeat/fake/expired/not_found/risk
    source: Mapped[str] = mapped_column(String(32), nullable=True)
    risk_reason: Mapped[str] = mapped_column(Text, nullable=True)
    elapsed_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    operator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    verified_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
