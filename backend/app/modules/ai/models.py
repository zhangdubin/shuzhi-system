"""
AI 平台模型（AI-API.md §8.1）
- ai_tasks: AI 任务表（字段抽取/风险扫描/匹配/Agent/起草）
- ai_feedback: AI 反馈表（数据回流）
- ai_alerts: AI 提醒表（Dashboard 顶部提醒）

不修改老表 schema（0 变更原则）。
"""
from datetime import datetime
from sqlalchemy import (
    String, Text, Integer, BigInteger, ForeignKey, DateTime, Numeric,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AITask(Base):
    """AI 任务表（每条 AI 调用都建一条记录）"""
    __tablename__ = "ai_tasks"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)  # 业务 ID
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # extract | risk | match | agent | generate
    sub_type: Mapped[str] = mapped_column(String(64), nullable=True)  # extract.invoice / risk.scan
    name: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")  # pending|running|done|failed|cancelled
    progress: Mapped[float] = mapped_column(Numeric(5, 4), default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    done_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    input: Mapped[dict] = mapped_column(JSONB, nullable=True)
    output: Mapped[dict] = mapped_column(JSONB, nullable=True)
    error: Mapped[dict] = mapped_column(JSONB, nullable=True)
    cost_cents: Mapped[int] = mapped_column(Integer, default=0)  # AI 调用成本（分）
    model: Mapped[str] = mapped_column(String(64), nullable=True)  # 用了哪个模型
    model_version: Mapped[str] = mapped_column(String(32), nullable=True)
    confidence: Mapped[float] = mapped_column(Numeric(5, 2), nullable=True)  # 综合置信度 0-100
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="web")  # web/ios/android/cron/api
    request_id: Mapped[str] = mapped_column(String(64), nullable=True)  # 关联请求 traceId
    ai_trace_id: Mapped[str] = mapped_column(String(64), nullable=True)  # AI 服务 traceId
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_ai_tasks_tenant_status", "tenant_id", "status"),
        Index("idx_ai_tasks_type_created", "type", "created_at"),
    )


class AIFeedback(Base):
    """AI 反馈表（数据回流，用于模型迭代）"""
    __tablename__ = "ai_feedback"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    target_type: Mapped[str] = mapped_column(String(32), nullable=False)  # extract | risk | ask | generate | match
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)  # 关联 ai_tasks.task_id
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    rating: Mapped[str] = mapped_column(String(8), nullable=False)  # up | down
    category: Mapped[str] = mapped_column(String(32), nullable=True)  # accurate | inaccurate | incomplete | not-helpful | other
    comment: Mapped[str] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(ARRAY(String), nullable=True)  # ["税率", "专票"]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        Index("idx_ai_feedback_target", "target_type", "target_id"),
        Index("idx_ai_feedback_user", "user_id", "created_at"),
    )


class AIAlert(Base):
    """AI 提醒表（Dashboard 顶部"今日 AI 助手提醒"）"""
    __tablename__ = "ai_alerts"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)  # NULL = 全员
    level: Mapped[str] = mapped_column(String(8), nullable=False)  # high | medium | low
    type: Mapped[str] = mapped_column(String(64), nullable=False)  # 业务类型 contract_overdue / expense_pending ...
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    action_url: Mapped[str] = mapped_column(String(512), nullable=True)
    action_label: Mapped[str] = mapped_column(String(64), nullable=True)
    object_type: Mapped[str] = mapped_column(String(32), nullable=True)  # 关联对象
    object_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="unread")  # unread | read | dismissed
    dismiss_remark: Mapped[str] = mapped_column(Text, nullable=True)
    snooze_until: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    read_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_ai_alerts_user_status", "user_id", "status", "created_at"),
    )
