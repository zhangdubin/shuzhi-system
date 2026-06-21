"""
公共模块 Schemas
- 字典 / 用户 / 客户 / 文件上传
"""
from typing import Optional
from pydantic import BaseModel, Field


# ===== 字典 =====

class DictItem(BaseModel):
    value: str
    label: str
    color: Optional[str] = None


class DictListResponse(BaseModel):
    list: list[DictItem]


# ===== 用户（下拉引用） =====

class UserBrief(BaseModel):
    userId: int
    name: str
    avatar: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None


class UserListRequest(BaseModel):
    keyword: str = ""
    departmentId: Optional[int] = None
    page: int = 1
    pageSize: int = Field(default=50, le=200)


class UserListResponse(BaseModel):
    list: list[UserBrief]
    total: int
    page: int
    pageSize: int


# ===== 客户（引用下拉） =====

class ClientBrief(BaseModel):
    clientId: int
    code: str
    name: str
    shortName: Optional[str] = None
    taxNo: Optional[str] = None
    level: Optional[str] = "C"


class ClientListRequest(BaseModel):
    keyword: str = ""
    page: int = 1
    pageSize: int = Field(default=50, le=200)


class ClientListResponse(BaseModel):
    list: list[ClientBrief]
    total: int
    page: int
    pageSize: int


# ===== 合同/项目引用（按客户过滤） =====

class ContractRef(BaseModel):
    contractId: int
    code: str
    name: str
    type: str
    amount: float  # 元
    status: str
    signDate: Optional[str] = None


class ProjectRef(BaseModel):
    projectId: int
    code: str
    name: str
    status: str
    managerName: Optional[str] = None


class RefListRequest(BaseModel):
    clientId: Optional[int] = None
    keyword: str = ""
    page: int = 1
    pageSize: int = Field(default=20, le=100)


class RefListResponse(BaseModel):
    list: list  # list[ContractRef] | list[ProjectRef]


# ===== 文件上传 =====

class FileInfo(BaseModel):
    fileId: str
    name: str
    size: int
    url: str
    type: Optional[str] = None
