"""
合同模块 Schemas
对应 API.md §合同管理
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field


class ContractListRequest(BaseModel):
    page: int = 1
    pageSize: int = Field(default=20, le=100)
    keyword: str = ""
    filters: dict = {}


class ContractBrief(BaseModel):
    contractId: int
    code: str
    name: str
    type: str
    status: str
    clientId: Optional[int] = None
    clientName: Optional[str] = None
    projectId: Optional[int] = None
    projectName: Optional[str] = None
    managerId: Optional[int] = None
    managerName: Optional[str] = None
    amount: Decimal
    currency: str = "CNY"
    signDate: Optional[date] = None
    effectiveDate: Optional[date] = None
    expireDate: Optional[date] = None
    createdAt: datetime


class ContractListResponse(BaseModel):
    list: list[ContractBrief]
    total: int
    page: int
    pageSize: int


class ContractDetail(BaseModel):
    contractId: int
    code: str
    name: str
    type: str
    status: str
    client: Optional[dict] = None
    projectId: Optional[int] = None
    projectName: Optional[str] = None
    managerId: Optional[int] = None
    managerName: Optional[str] = None
    amount: Decimal
    currency: str
    signDate: Optional[date] = None
    effectiveDate: Optional[date] = None
    expireDate: Optional[date] = None
    duration: Optional[str] = None
    paymentMethod: Optional[str] = None
    paymentTerm: Optional[str] = None
    summary: Optional[str] = None
    terms: list[dict] = []
    approvalFlow: Optional[dict] = None
    signatures: dict = {}
    attachments: list[dict] = []
    performance: dict = {}
    createdBy: Optional[int] = None
    createdAt: datetime
    updatedAt: datetime


class ContractCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    type: str  # sales/purchase/service/framework
    clientId: Optional[int] = None
    projectId: Optional[int] = None
    managerId: int
    amount: int  # 元（后端自动 *100 存分）
    currency: str = "CNY"
    signDate: Optional[date] = None
    effectiveDate: Optional[date] = None
    expireDate: Optional[date] = None
    paymentMethod: Optional[str] = None
    paymentTerm: Optional[str] = None
    summary: Optional[str] = None
    fileId: Optional[str] = None
    templateId: Optional[int] = None


class ContractUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    clientId: Optional[int] = None
    projectId: Optional[int] = None
    managerId: Optional[int] = None
    amount: Optional[int] = None
    signDate: Optional[date] = None
    effectiveDate: Optional[date] = None
    expireDate: Optional[date] = None
    paymentMethod: Optional[str] = None
    paymentTerm: Optional[str] = None
    summary: Optional[str] = None


class ContractApproveRequest(BaseModel):
    contractId: int
    action: str  # approve/reject/transfer
    comment: Optional[str] = None
    transferTo: Optional[int] = None


class ContractStatsResponse(BaseModel):
    total: int
    executed: int
    totalAmount: Decimal
    pendingApproval: int
    expiringSoon: int


class ContractTemplateItem(BaseModel):
    id: int
    name: str
    type: str
