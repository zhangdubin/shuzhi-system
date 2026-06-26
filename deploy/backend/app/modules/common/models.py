"""
公共模块模型
- File: 通用文件
- Client: 客户（完整版，BACKEND.md §3.2）
- Notification: 通知
"""
from datetime import datetime
from sqlalchemy import String, Text, Integer, BigInteger, ForeignKey, Boolean, Date
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class File(Base):
    """文件（通用）"""
    __tablename__ = "files"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)  # F-2026-001
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    ext: Mapped[str] = mapped_column(String(16), nullable=True)
    size: Mapped[int] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[str] = mapped_column(String(64), nullable=True)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    storage: Mapped[str] = mapped_column(String(16), default="local")  # local/s3/oss
    uploader_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    biz_type: Mapped[str] = mapped_column(String(32), nullable=True)  # invoice/contract/expense
    biz_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class Client(Base):
    """客户（完整版，对应 BACKEND.md §3.2）"""
    __tablename__ = "clients"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    short_name: Mapped[str] = mapped_column(String(64), nullable=True)
    tax_no: Mapped[str] = mapped_column(String(32), nullable=True)
    legal_person: Mapped[str] = mapped_column(String(32), nullable=True)
    contact_name: Mapped[str] = mapped_column(String(32), nullable=True)
    contact_phone: Mapped[str] = mapped_column(String(20), nullable=True)
    contact_email: Mapped[str] = mapped_column(String(128), nullable=True)
    address: Mapped[str] = mapped_column(String(256), nullable=True)
    bank_name: Mapped[str] = mapped_column(String(64), nullable=True)
    bank_account: Mapped[str] = mapped_column(String(32), nullable=True)
    industry: Mapped[str] = mapped_column(String(32), nullable=True)
    level: Mapped[str] = mapped_column(String(16), default="C")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[str] = mapped_column(Text, nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)


class Notification(Base):
    """通知"""
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # todo/mention/system
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=True)
    link: Mapped[str] = mapped_column(String(256), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    read_at: Mapped[datetime] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


# ============================================================
# 通用审批流（BACKEND.md §3.3，放在 common 是为了让 approvals 引擎
# 不被 expense 模块反向循环 import）
# ============================================================
class ApprovalFlow(Base):
    """通用审批流"""
    __tablename__ = "approval_flows"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    business_type: Mapped[str] = mapped_column(String(32), nullable=False)  # expense/contract/...
    business_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    template_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="in_progress", index=True)
    current_step: Mapped[int] = mapped_column(Integer, default=1)
    total_steps: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    finished_at: Mapped[datetime] = mapped_column(nullable=True)




class ApprovalTemplate(Base):
    """审批流模板（可由超管配置）
    - business_type: 'expense' / 'contract' / ...
    - rules: JSON 数组，按顺序定义步骤规则
      例：["submitter", "direct_leader", "finance", "gm_if_over_5000"]
    - condition: 可选 JSON，触发条件
      例：{"amount_min": 500000} 表示金额 >= 5000 元才用此模板
    - is_default: 同一 business_type 下唯一默认模板（无匹配时兜底）
    """
    __tablename__ = "approval_templates"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    business_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    rules: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    condition: Mapped[dict] = mapped_column(JSONB, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    remark: Mapped[str] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

class ApprovalStep(Base):
    """审批步骤"""
    __tablename__ = "approval_steps"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    flow_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("approval_flows.id", ondelete="CASCADE"), index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    approver_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="todo")
    action: Mapped[str] = mapped_column(String(16), nullable=True)
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    trigger_rule: Mapped[str] = mapped_column(String(256), nullable=True)
    finished_at: Mapped[datetime] = mapped_column(nullable=True)
