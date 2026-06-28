"""UDPE 模块 Pydantic Schemas。

设计文档：plans/udpe-design/design.md §五 5.3
"""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ===== 模板管理 =====

class PrintTemplateOut(BaseModel):
    id: int
    code: str
    name: str
    docType: str
    paper: str
    widthMm: float
    heightMm: float
    orientation: str
    status: str
    isDefault: bool
    description: Optional[str] = None
    schemaJson: dict = Field(default_factory=dict, alias="schemaJson")
    version: int
    createdBy: Optional[int] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    class Config:
        populate_by_name = True


class PrintTemplateListResponse(BaseModel):
    list: list[PrintTemplateOut]
    total: int


class PrintTemplateCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=128)
    docType: str = Field(..., min_length=1, max_length=32)
    paper: str = "A4"
    widthMm: float = 210
    heightMm: float = 297
    orientation: str = "portrait"
    description: Optional[str] = None
    schemaJson: dict = Field(default_factory=dict, alias="schemaJson")
    isDefault: bool = False
    # 设计决策 ADR-11：V1 不强制校验，但保留 JSONSchema 入口
    inputSchema: Optional[dict] = None

    class Config:
        populate_by_name = True


class PrintTemplateUpdate(BaseModel):
    name: Optional[str] = None
    paper: Optional[str] = None
    widthMm: Optional[float] = None
    heightMm: Optional[float] = None
    orientation: Optional[str] = None
    description: Optional[str] = None
    schemaJson: Optional[dict] = Field(default=None, alias="schemaJson")
    isDefault: Optional[bool] = None
    inputSchema: Optional[dict] = None
    versionNote: Optional[str] = None  # 更新时备注（用于版本快照）

    class Config:
        populate_by_name = True


# ===== 运行时 =====

class PrintOptions(BaseModel):
    copies: int = 1
    watermark: Optional[str] = None
    paper: Optional[str] = None
    renderMode: str = "pdf"  # "html" | "pdf"
    locale: str = "zh"  # 多语言：zh / en / ja / ko 等
    sourceModule: Optional[str] = None
    sourceId: Optional[str] = None


class PrintRequest(BaseModel):
    templateCode: str
    data: dict = Field(default_factory=dict)
    options: Optional[PrintOptions] = None


class PrintPreviewResponse(BaseModel):
    html: str
    templateId: int
    logId: int
    templateCode: str
    templateName: str


class PrintLogOut(BaseModel):
    id: int
    templateId: Optional[int] = None
    templateCode: str
    docType: str
    action: str
    status: str
    operatorId: Optional[int] = None
    operatorName: Optional[str] = None
    sourceModule: Optional[str] = None
    sourceId: Optional[str] = None
    elapsedMs: Optional[int] = None
    errorMsg: Optional[str] = None
    pdfSize: Optional[int] = None
    createdAt: Optional[datetime] = None


class PrintPreviewBySchemaRequest(BaseModel):
    """M3 阶段 1: 编辑器实时预览 - 不依赖已保存的 templateCode, 直接传 schemaJson."""
    docType: str = Field(..., min_length=1, max_length=32)
    schemaJson: dict = Field(default_factory=dict)
    data: dict = Field(default_factory=dict)
    options: Optional[PrintOptions] = None


class PrintBatchItem(BaseModel):
    """批量打印的单条记录标识 (id: business primary key)."""
    id: str | int


class PrintBatchRequest(BaseModel):
    """批量打印请求 (M2 阶段 9). V1 限制: 同一模板, items 数量 1-100."""
    templateCode: str = Field(..., min_length=1, max_length=64)
    items: list[PrintBatchItem] = Field(..., min_length=1, max_length=100)
    options: Optional[PrintOptions] = None


class PrintBatchResponse(BaseModel):
    """批量打印响应 (合并后下载 URL 由 /print/pdf 端点提供, 此处仅给统计)."""
    total: int
    success: int
    failed: int
    logIds: list[int]
    failedItems: list[dict] = Field(default_factory=list)
    elapsedMs: int


class PrintLogListResponse(BaseModel):
    list: list[PrintLogOut]
    total: int
