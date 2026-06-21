"""
报销中心数据模型
- reimbursement_forms  报销单
- reimbursement_details 报销明细（关联 expense）
"""
from datetime import date, datetime
from sqlalchemy import String, Text, Integer, BigInteger, ForeignKey, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class ReimbursementForm(Base):
    __tablename__ = "reimbursement_forms"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    form_no: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    template_type: Mapped[str] = mapped_column(String(32), nullable=False, default="general")
    # general / travel / hospitality / marketing / custom
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    applicant_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    department_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("departments.id"), nullable=True)
    total_amount: Mapped[int] = mapped_column(BigInteger, default=0)            # 申请金额（分）
    actual_amount: Mapped[int] = mapped_column(BigInteger, default=0)           # 实际报销金额（分）
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    # 状态：draft / printed / submitted / reimbursed / done / cancelled
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=True)              # 报销发生日期
    payment_date: Mapped[date] = mapped_column(Date, nullable=True)              # 实际支付日期
    voucher_no: Mapped[str] = mapped_column(String(64), nullable=True)          # 凭证号
    ai_description: Mapped[str] = mapped_column(Text, nullable=True)            # AI 生成的报销说明
    ai_risk_flag: Mapped[str] = mapped_column(String(16), nullable=True)         # AI 风险等级
    ai_risk_reason: Mapped[str] = mapped_column(Text, nullable=True)
    remark: Mapped[str] = mapped_column(Text, nullable=True)
    template_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=True)        # 模板快照（JSON）
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    applicant: Mapped["User"] = relationship(foreign_keys=[applicant_id])
    department: Mapped["Department"] = relationship(foreign_keys=[department_id])
    details: Mapped[list["ReimbursementDetail"]] = relationship(
        back_populates="form", cascade="all, delete-orphan"
    )


class ReimbursementDetail(Base):
    """报销明细（关联销售费用 expense）"""
    __tablename__ = "reimbursement_details"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    form_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("reimbursement_forms.id", ondelete="CASCADE"), index=True
    )
    expense_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("expenses.id", ondelete="RESTRICT"), index=True
    )
    expense_code: Mapped[str] = mapped_column(String(32), nullable=True)
    expense_type: Mapped[str] = mapped_column(String(32), nullable=True)
    expense_date: Mapped[date] = mapped_column(Date, nullable=True)
    client_name: Mapped[str] = mapped_column(String(128), nullable=True)
    project_name: Mapped[str] = mapped_column(String(128), nullable=True)
    title: Mapped[str] = mapped_column(String(128), nullable=True)
    amount: Mapped[int] = mapped_column(BigInteger, default=0)        # 分
    reimbursed_amount: Mapped[int] = mapped_column(BigInteger, default=0)  # 已回填金额（分）
    remark: Mapped[str] = mapped_column(Text, nullable=True)
    seq: Mapped[int] = mapped_column(Integer, default=0)

    form: Mapped["ReimbursementForm"] = relationship(back_populates="details")


class ReimbursementTemplate(Base):
    """报销模板（自定义 + 内置）"""
    __tablename__ = "reimbursement_templates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)  # 全局唯一
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[str] = mapped_column(String(32), default="custom", index=True)  # general/travel/hospitality/marketing/custom
    icon: Mapped[str] = mapped_column(String(8), default="📋")
    color: Mapped[str] = mapped_column(String(16), default="#4F6BFF")
    description: Mapped[str] = mapped_column(String(256), nullable=True)
    schema_json: Mapped[dict] = mapped_column(JSONB, nullable=False)  # 完整 schema
    is_system: Mapped[int] = mapped_column(Integer, default=0)  # 1=系统内置（只读），0=用户自定义
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)
