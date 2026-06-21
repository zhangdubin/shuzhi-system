"""
项目 Pydantic schemas
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ===== 列表筛选 =====

class ProjectListRequest(BaseModel):
    page: int = 1
    pageSize: int = Field(default=20, le=100)
    keyword: str = ""
    view: str = "list"  # list/kanban/gantt
    filters: dict = {}


# ===== 响应模型 =====

class ProjectInfo(BaseModel):
    id: int
    code: str
    name: str
    type: Optional[str] = None
    status: str
    clientId: Optional[int] = None
    clientName: Optional[str] = None
    managerId: Optional[int] = None
    managerName: Optional[str] = None
    startDate: Optional[date] = None
    endDate: Optional[date] = None
    contractAmount: Decimal  # 元
    budget: Decimal
    spent: Decimal
    progress: Decimal  # 0-100
    description: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime


class ProjectListResponse(BaseModel):
    list: list[ProjectInfo]
    total: int
    page: int
    pageSize: int


# ===== 创建/更新 =====

class ProjectCreate(BaseModel):
    code: Optional[str] = None  # 可选，后端自动生成
    name: str = Field(..., min_length=1, max_length=128)
    type: Optional[str] = None
    status: Optional[str] = "planning"
    clientId: Optional[int] = None
    clientName: Optional[str] = None
    managerId: Optional[int] = None
    managerName: Optional[str] = None
    startDate: Optional[date] = None
    endDate: Optional[date] = None
    contractAmount: Decimal = Decimal("0")  # 元，service转分
    budget: Decimal = Decimal("0")          # 元，service转分
    spent: Decimal = Decimal("0")           # 元，service转分
    progress: Decimal = Decimal("0")        # 0-100
    description: Optional[str] = None

    @field_validator("startDate", "endDate", mode="before")
    @classmethod
    def _empty_str_to_none(cls, v):
        # 接受空字符串 / 无效值 → None，避免 Pydantic 报 422
        if v is None or v == "":
            return None
        return v

    @model_validator(mode="after")
    def check_dates(self):
        if self.startDate and self.endDate and self.endDate < self.startDate:
            raise ValueError("截止日期必须晚于开始日期")
        return self


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    clientId: Optional[int] = None
    managerId: Optional[int] = None
    status: Optional[str] = None
    startDate: Optional[date] = None
    endDate: Optional[date] = None
    budget: Optional[int] = None
    spent: Optional[int] = None
    progress: Optional[Decimal] = None
    description: Optional[str] = None
    remark: Optional[str] = None

    @field_validator("startDate", "endDate", mode="before")
    @classmethod
    def _empty_str_to_none(cls, v):
        if v is None or v == "":
            return None
        return v


# ===== 里程碑 =====

class MilestoneInfo(BaseModel):
    id: int
    name: str
    seq: int
    status: str
    plannedStart: Optional[date] = None
    plannedEnd: Optional[date] = None
    completedAt: Optional[datetime] = None
    progress: Decimal = 0
    remark: Optional[str] = None


class MilestoneCreate(BaseModel):
    name: str
    plannedStart: Optional[date] = None
    plannedEnd: Optional[date] = None
    operatorId: Optional[int] = None
    remark: Optional[str] = None


# ===== 统计 =====

class ProjectStatsResponse(BaseModel):
    active: int
    newThisMonth: int
    completedThisMonth: int
    expiringSoon: int
    totalContractAmount: Decimal
