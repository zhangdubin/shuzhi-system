"""
安全模块：JWT 签发/校验、密码加密
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, Header
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.core.database import get_db
from app.core.exceptions import UnauthorizedException, ForbiddenException
from app.modules.auth.models import User

# 密码加密（bcrypt）
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """密码加密"""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """密码校验"""
    return pwd_context.verify(plain, hashed)


# ===== JWT =====

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """签发 access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """签发 refresh token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """解析 token"""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise UnauthorizedException("Token 无效或已过期")


# ===== 当前用户 =====

class CurrentUser:
    """当前用户信息（请求级别）"""
    def __init__(self, user: User, permissions: list[str], data_scope: str):
        self.user = user
        self.permissions = permissions  # 用户拥有的权限 code 列表
        self.data_scope = data_scope    # all/dept/dept_sub/self/custom
        self.id = user.id
        self.username = user.username
        self.name = user.name
        self.is_admin = user.is_admin
        self.department_id = user.department_id

    def has_permission(self, perm_code: str) -> bool:
        if self.is_admin:
            return True
        return perm_code in self.permissions

    def can_access(self, resource_owner_id: int) -> bool:
        """检查当前用户是否可访问某资源（基于 data_scope）"""
        if self.is_admin or self.data_scope == "all":
            return True
        if self.data_scope == "self":
            return resource_owner_id == self.id
        # dept / custom 实际场景更复杂，这里简化为同部门
        # 真实实现需要 join 用户表判断
        return True  # TODO: 实现完整的部门数据范围


async def get_current_user(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> CurrentUser:
    """FastAPI 依赖：获取当前登录用户"""
    if not authorization or not authorization.startswith("Bearer "):
        raise UnauthorizedException()

    token = authorization.replace("Bearer ", "").strip()
    payload = decode_token(token)
    user_id = payload.get("sub")

    if not user_id:
        raise UnauthorizedException()

    # 查询用户（含角色 + 权限）
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(User)
        .where(User.id == int(user_id), User.is_active == True)
        .options(selectinload(User.department))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise UnauthorizedException("用户不存在或已禁用")

    # 收集权限（直接走 user_roles → role_permissions → permissions 三表 join）
    # 真实项目可以用 Redis 缓存
    from app.modules.auth.models import Role, Permission, UserRole, RolePermission
    perms_result = await db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
    )
    permissions = list({row[0] for row in perms_result.all()})
    # R11B：is_admin（super admin）自动加 '*' 通配符，前端 v-permission 走 super admin 放行
    if user.is_admin:
        permissions.append('*')

    # 取最高数据范围
    scope_result = await db.execute(
        select(Role.data_scope)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user.id)
        .order_by(Role.data_scope.desc())  # all > dept_sub > dept > self
    )
    scopes = [row[0] for row in scope_result.all()]
    data_scope = "all" if "all" in scopes else (scopes[0] if scopes else "self")

    return CurrentUser(user, permissions, data_scope)


# 简写
get_current_user_dep = get_current_user


def require_permission(perm_code: str):
    """权限检查装饰器"""
    async def _check(current_user: CurrentUser = Depends(get_current_user_dep)) -> CurrentUser:
        if not current_user.has_permission(perm_code):
            raise ForbiddenException(f"无权限：{perm_code}")
        return current_user
    return _check


def require_admin():
    """仅超级管理员可访问"""
    async def _check(current_user: CurrentUser = Depends(get_current_user_dep)) -> CurrentUser:
        if not getattr(current_user, "is_admin", False):
            raise ForbiddenException("仅超级管理员可访问该接口")
        return current_user
    return _check
