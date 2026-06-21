"""
认证模块：用户、角色、权限、字典、审计日志
对应 BACKEND.md §3.1 用户与权限 + §3.5 公共
"""
from datetime import datetime
from sqlalchemy import String, Boolean, Integer, ForeignKey, Text, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    parent_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("departments.id"), nullable=True)
    manager_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系（admin 模块用了 selectinload）
    # parent_id 字段有 FK；manager_id 字段 BACKEND.md §3.1 不带 FK，需 primaryjoin 显式连
    parent: Mapped["Department"] = relationship(remote_side="Department.id", foreign_keys=[parent_id])
    manager: Mapped["User"] = relationship(
        primaryjoin="Department.manager_id == User.id",
        foreign_keys="[Department.manager_id]",
        viewonly=True,
    )


class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    data_scope: Mapped[str] = mapped_column(String(16), default="self")  # all/dept/dept_sub/self/custom
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # 关系
    permissions: Mapped[list["Permission"]] = relationship(secondary="role_permissions", back_populates="roles")
    users: Mapped[list["User"]] = relationship(secondary="user_roles", back_populates="roles")


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    resource: Mapped[str] = mapped_column(String(32), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    roles: Mapped[list["Role"]] = relationship(secondary="role_permissions", back_populates="permissions")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(128), unique=True, nullable=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    avatar: Mapped[str] = mapped_column(String(256), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    department_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("departments.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime] = mapped_column(nullable=True)
    last_login_ip: Mapped[str] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, onupdate=datetime.utcnow)

    department: Mapped["Department"] = relationship(foreign_keys=[department_id])
    roles: Mapped[list["Role"]] = relationship(secondary="user_roles", back_populates="users")


class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


class DictType(Base):
    """字典分类（元信息）— 独立于字典项，方便前端展示/管理"""
    __tablename__ = "dict_types"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(256), nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class Dictionary(Base):
    """字典表（费用类型/合同类型等）"""
    __tablename__ = "dictionaries"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    dict_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    color: Mapped[str] = mapped_column(String(16), nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str] = mapped_column(String(256), nullable=True)


class AuditLog(Base):
    """审计日志"""
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    operator_id: Mapped[int] = mapped_column(BigInteger, nullable=True, index=True)
    operator_name: Mapped[str] = mapped_column(String(32), nullable=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    resource_code: Mapped[str] = mapped_column(String(64), nullable=True, index=True)  # 业务对象编码（合同号/用户名/编号）
    path: Mapped[str] = mapped_column(String(256), nullable=True)
    method: Mapped[str] = mapped_column(String(8), nullable=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=True)
    ip: Mapped[str] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str] = mapped_column(String(256), nullable=True)
    elapsed_ms: Mapped[int] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow, index=True)
