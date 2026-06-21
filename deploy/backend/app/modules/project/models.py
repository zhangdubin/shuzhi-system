"""
项目模块：完整 CRUD + 列表筛选 + 统计
这是其他模块的"样板"——结构最完整（关联用户/客户/团队/里程碑）

注意：Client 模型统一在 app.modules.common.models（BACKEND.md §3.2 完整版），
不再在本地重复定义。
"""
from datetime import date, datetime
from sqlalchemy import String, Text, Integer, ForeignKey, BigInteger, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base
# 复用 common 模块的 Client（解决重复定义问题）
from app.modules.common.models import Client  # noqa: F401
# 解决 relationship("User", ...) 字符串引用——必须显式 import
from app.modules.auth.models import User  # noqa: F401


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(32), nullable=True)
    client_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("clients.id"))
    manager_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(16), default="planning", index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=True)
    contract_amount: Mapped[int] = mapped_column(BigInteger, default=0)  # 分
    budget: Mapped[int] = mapped_column(BigInteger, default=0)
    spent: Mapped[int] = mapped_column(BigInteger, default=0)
    progress: Mapped[Numeric] = mapped_column(Numeric(5, 2), default=0)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    client: Mapped["Client"] = relationship()
    manager = relationship("User", foreign_keys=[manager_id])
    milestones: Mapped[list["ProjectMilestone"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class ProjectMilestone(Base):
    __tablename__ = "project_milestones"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="todo")  # done/current/todo
    planned_start: Mapped[date] = mapped_column(Date, nullable=True)
    planned_end: Mapped[date] = mapped_column(Date, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(nullable=True)
    progress: Mapped[Numeric] = mapped_column(Numeric(5, 2), default=0)
    operator_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    remark: Mapped[str] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="milestones")


class ProjectTeam(Base):
    __tablename__ = "project_team"
    project_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(32), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
