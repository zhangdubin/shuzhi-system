"""
回款 Schemas
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class ReceivableListRequest(BaseModel):
    page: int = 1
    pageSize: int = Field(default=20, le=100)
    keyword: str = ""
    filters: dict = {}


class ReceivableBrief(BaseModel):
    receivableId: int
    code: str
    contractId: Optional[int] = None
    contractCode: Optional[str] = None
    clientId: Optional[int] = None
    clientName: Optional[str] = None
    type: Optional[str] = None
    planAmount: Decimal
    receivedAmount: Decimal
    pendingAmount: Decimal
    planDate: date
    actualDate: Optional[date] = None
    overdueDays: int
    managerId: Optional[int] = None
    managerName: Optional[str] = None
    status: str
    createdAt: datetime


class ReceivableListResponse(BaseModel):
    list: list[ReceivableBrief]
    total: int
    page: int
    pageSize: int


class ReceivableDetail(BaseModel):
    receivableId: int
    code: str
    contractId: Optional[int] = None
    client: Optional[dict] = None
    type: Optional[str] = None
    planAmount: Decimal
    receivedAmount: Decimal
    pendingAmount: Decimal
    planDate: date
    actualDate: Optional[date] = None
    overdueDays: int
    term: Optional[str] = None
    manager: Optional[dict] = None
    bankAccount: Optional[dict] = None
    status: str
    remark: Optional[str] = None
    history: list[dict] = []
    remindLogs: list[dict] = []
    linkedInvoices: list[dict] = []
    clientPaymentHistory: list[dict] = []
    riskAssessment: dict = {}
    createdAt: datetime
    updatedAt: datetime


class ReceivableCreate(BaseModel):
    contractId: Optional[int] = None
    clientId: Optional[int] = None
    type: Optional[str] = None
    planAmount: int  # 元（后端 *100 存分）
    receivedAmount: int = 0  # 元（后端 *100 存分）
    actualDate: Optional[date] = None
    planDate: date
    termDays: int = 30
    managerId: Optional[int] = None
    bankAccount: Optional[str] = None
    remark: Optional[str] = None


class ReceivableUpdate(BaseModel):
    """部分更新（所有字段可选）"""
    type: Optional[str] = None
    planAmount: Optional[int] = None
    actualDate: Optional[date] = None
    planDate: Optional[date] = None
    managerId: Optional[int] = None
    remark: Optional[str] = None


class ReceivableRemindRequest(BaseModel):
    receivableId: int
    type: str  # phone/email/wechat
    contactPerson: Optional[str] = None
    content: Optional[str] = None
    attachments: list[str] = []


class ReceivableReceiveRequest(BaseModel):
    receivableId: int
    receivedAmount: int  # 分
    receivedDate: date
    bankStatement: Optional[str] = None  # fileId
    remark: Optional[str] = None


class ReceivableStatsResponse(BaseModel):
    kpi: dict
    monthTimeline: list[dict]
    topClients: list[dict]
