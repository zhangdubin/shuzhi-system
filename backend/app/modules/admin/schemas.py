"""
管理后台 Schemas
- 部门 / 角色 / 权限 / 用户 / 字典 / 审计
"""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


# ============================================================
# 部门
# ============================================================

class DeptInfo(BaseModel):
    id: int
    name: str
    code: str
    parentId: Optional[int] = None
    parentName: Optional[str] = None
    managerId: Optional[int] = None
    managerName: Optional[str] = None
    sort: int = 0
    isActive: bool = True
    memberCount: int = 0
    createdAt: Optional[datetime] = None


class DeptListResponse(BaseModel):
    list: list[DeptInfo]
    total: int


class DeptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    code: str = Field(..., min_length=1, max_length=32)
    parentId: Optional[int] = None
    managerId: Optional[int] = None
    sort: int = 0
    isActive: bool = True


class DeptUpdate(BaseModel):
    name: Optional[str] = None
    parentId: Optional[int] = None
    managerId: Optional[int] = None
    sort: Optional[int] = None
    isActive: Optional[bool] = None


# ============================================================
# 角色
# ============================================================

class PermissionInfo(BaseModel):
    id: int
    code: str
    resource: str
    action: str
    name: str
    description: Optional[str] = None


class PermissionListResponse(BaseModel):
    list: list[PermissionInfo]
    total: int


class RoleInfo(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    isBuiltin: bool = False
    dataScope: str = "self"  # all/dept/dept_sub/self/custom
    userCount: int = 0
    permissionCount: int = 0
    permissions: list[str] = []  # permission codes
    createdAt: Optional[datetime] = None


class RoleListResponse(BaseModel):
    list: list[RoleInfo]
    total: int


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=32)
    code: str = Field(..., min_length=1, max_length=32)
    description: Optional[str] = None
    dataScope: str = "self"
    permissionCodes: list[str] = []


class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    dataScope: Optional[str] = None
    permissionCodes: Optional[list[str]] = None


# ============================================================
# 用户
# ============================================================

class UserInfoAdmin(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    phone: Optional[str] = None
    name: str
    avatar: Optional[str] = None
    departmentId: Optional[int] = None
    departmentName: Optional[str] = None
    roleIds: list[int] = []
    roleNames: list[str] = []
    roleCodes: list[str] = []
    permissionCount: int = 0
    isActive: bool = True
    isAdmin: bool = False
    lastLoginAt: Optional[datetime] = None
    lastLoginIp: Optional[str] = None
    createdAt: Optional[datetime] = None


class UserListRequest(BaseModel):
    page: int = 1
    pageSize: int = Field(default=20, le=100)
    keyword: str = ""
    departmentId: Optional[int] = None
    roleId: Optional[int] = None
    isActive: Optional[bool] = None


class UserListResponse(BaseModel):
    list: list[UserInfoAdmin]
    total: int
    page: int
    pageSize: int


class UserCreate(BaseModel):
    # 同时支持 username / account 两种命名
    username: Optional[str] = Field(None, min_length=1, max_length=32)
    account: Optional[str] = Field(None, min_length=1, max_length=32)
    password: str = Field(..., min_length=6, max_length=128)
    name: str = Field(..., min_length=1, max_length=32)
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    departmentId: Optional[int] = None
    roleIds: list[int] = []
    isAdmin: bool = False

    def get_username(self) -> str:
        return self.username or self.account or ""


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    avatar: Optional[str] = None
    departmentId: Optional[int] = None
    roleIds: Optional[list[int]] = None
    isActive: Optional[bool] = None
    isAdmin: Optional[bool] = None


class UserResetPassword(BaseModel):
    userId: int
    newPassword: str = Field(..., min_length=6, max_length=128)


class UserBatchDelete(BaseModel):
    userIds: list[int] = Field(..., min_length=1)


class UserToggleActive(BaseModel):
    userId: int
    isActive: bool


# ============================================================
# 字典
# ============================================================

class DictTypeCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=64)
    description: Optional[str] = None


class DictTypeUpdate(BaseModel):
    id: int
    name: Optional[str] = None
    description: Optional[str] = None
    sort: Optional[int] = None


class DictItemAdmin(BaseModel):
    id: int
    dictType: str
    value: str
    label: str
    color: Optional[str] = None
    sort: int = 0
    isActive: bool = True


class DictListByTypeResponse(BaseModel):
    list: list[DictItemAdmin]
    total: int


class DictCreate(BaseModel):
    dictType: str = Field(..., min_length=1, max_length=32)
    value: str = Field(..., min_length=1, max_length=64)
    label: str = Field(..., min_length=1, max_length=64)
    color: Optional[str] = None
    sort: int = 0
    isActive: bool = True
    description: Optional[str] = None


class DictUpdate(BaseModel):
    label: Optional[str] = None
    value: Optional[str] = None
    color: Optional[str] = None
    sort: Optional[int] = None
    isActive: Optional[bool] = None
    description: Optional[str] = None


# ============================================================
# 审计日志
# ============================================================

class AuditLogInfo(BaseModel):
    id: int
    operatorId: Optional[int] = None
    operatorName: Optional[str] = None
    action: str  # POST/PUT/DELETE/PATCH
    resourceType: str
    resourceId: Optional[int] = None
    resourceCode: Optional[str] = None
    path: Optional[str] = None
    method: Optional[str] = None
    statusCode: Optional[int] = None
    ip: Optional[str] = None
    userAgent: Optional[str] = None
    elapsedMs: Optional[int] = None
    body: Optional[str] = None
    createdAt: datetime


class AuditLogListRequest(BaseModel):
    page: int = 1
    pageSize: int = Field(default=20, le=100)
    keyword: str = ""
    filters: dict = {}


class AuditLogListResponse(BaseModel):
    list: list[AuditLogInfo]
    total: int
    page: int
    pageSize: int
