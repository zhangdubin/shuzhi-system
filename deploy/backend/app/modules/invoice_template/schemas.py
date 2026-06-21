"""
发票模板 Schemas
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel, Field


class TemplateListRequest(BaseModel):
    page: int = 1
    pageSize: int = Field(default=12, le=50)
    filters: dict = {}


class TemplateField(BaseModel):
    id: Optional[str] = None
    label: str
    key: str
    type: str  # text/date/amount/rate/user/ref/textarea
    required: bool = False
    aiSupport: bool = True
    defaultValue: Optional[Any] = None
    linkedField: Optional[str] = None
    refType: Optional[str] = None
    options: Optional[list] = None


class TemplateBrief(BaseModel):
    templateId: int
    code: str
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    icon: Optional[str] = None
    iconColor: list[str] = []
    fieldCount: int = 0
    usageCount: int = 0
    relatedProjectCount: int = 0
    rating: float = 5.0
    status: str = "enabled"
    isPinned: bool = False
    isMarket: bool = False
    creator: Optional[dict] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class TemplateListResponse(BaseModel):
    list: list[TemplateBrief]
    total: int
    page: int
    pageSize: int


class TemplateDetail(BaseModel):
    templateId: int
    code: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    defaultTaxRate: float = 0
    fields: list[TemplateField] = []
    creator: Optional[dict] = None
    createdAt: datetime
    updatedAt: datetime


class TemplateSave(BaseModel):
    templateId: Optional[int] = None
    code: Optional[str] = None
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    defaultTaxRate: float = 0
    icon: Optional[str] = None
    iconColors: Optional[str] = None
    fields: list[TemplateField] = []


class TemplateDuplicate(BaseModel):
    templateId: int


class TemplateDelete(BaseModel):
    templateId: int


class FieldLibraryResponse(BaseModel):
    groups: list[dict]
