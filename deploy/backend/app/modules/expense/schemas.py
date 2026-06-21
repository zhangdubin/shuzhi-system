"""
销售费用 Schemas
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class ExpenseListRequest(BaseModel):
    page: int = 1
    pageSize: int = Field(default=20, le=100)
    keyword: str = ""
    filters: dict = {}


class ExpenseBrief(BaseModel):
    expenseId: int
    code: str
    category: str
    title: str
    amount: Decimal
    currency: str = "CNY"
    expenseDate: date
    applicantId: int
    applicantName: str
    departmentId: Optional[int] = None
    departmentName: Optional[str] = None
    status: str
    submitAt: Optional[datetime] = None
    createdAt: datetime


class ExpenseListResponse(BaseModel):
    list: list[ExpenseBrief]
    total: int
    page: int
    pageSize: int


class ExpenseBreakdownItem(BaseModel):
    label: str
    amount: int  # 分
    remark: Optional[str] = None


class ExpenseAttachment(BaseModel):
    fileId: str
    name: str
    size: int
    type: Optional[str] = None
    ocrStatus: Optional[str] = None


class ExpenseDetail(BaseModel):
    expenseId: int
    code: str
    category: str
    title: str
    description: Optional[str] = None
    amount: Decimal
    currency: str
    expenseDate: date
    submitDate: Optional[datetime] = None
    applicant: dict
    department: Optional[dict] = None
    contractId: Optional[int] = None
    projectId: Optional[int] = None
    breakdown: list[ExpenseBreakdownItem] = []
    attachments: list[ExpenseAttachment] = []
    approvalFlow: Optional[dict] = None
    status: str
    createdAt: datetime
    updatedAt: datetime


class ExpenseCreate(BaseModel):
    category: str
    title: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    amount: int  # 元（前端传元，后端 *100 存分）
    expenseDate: date
    contractId: Optional[int] = None
    projectId: Optional[int] = None
    breakdown: list[ExpenseBreakdownItem] = []
    attachmentIds: list[str] = []


class ExpenseUpdate(BaseModel):
    """部分更新（所有字段可选）"""
    category: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    amount: Optional[int] = None
    expenseDate: Optional[date] = None
    contractId: Optional[int] = None
    projectId: Optional[int] = None
    breakdown: Optional[list[ExpenseBreakdownItem]] = None


class ExpenseApproveRequest(BaseModel):
    expenseId: int
    action: str  # approve/reject/transfer
    comment: Optional[str] = None
    transferTo: Optional[int] = None


class ExpenseKPI(BaseModel):
    totalAmount: Decimal
    pendingCount: int
    pendingAmount: Decimal
    approvedCount: int
    rejectedCount: int


class ExpenseStatsResponse(BaseModel):
    kpi: ExpenseKPI
    trendChart: dict
    categoryChart: list[dict]
