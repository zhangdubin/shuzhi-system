"""
AI 平台 Schemas（AI-API.md §6）
9 个子模块：extract / risk / ask / alert / task / feedback / model / stats / stream
"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


# ============================================================
# 通用：AI Meta（所有 AI 输出 data 必带）
# ============================================================
class AIMeta(BaseModel):
    model: str
    version: str
    confidence: float
    durationMs: int
    costCents: int
    traceId: str
    tokensUsed: Optional[int] = None


# ============================================================
# 6.1 字段抽取
# ============================================================
class ExtractField(BaseModel):
    """字段级 AI 输出（含 confidence）"""
    value: Any
    confidence: float  # 0-100
    bbox: Optional[list[int]] = None
    needsReview: Optional[bool] = None


class ExtractUploadRequest(BaseModel):
    fileId: str
    fileUrl: str
    type: str = "invoice"  # invoice | contract | receipt | business-card | bank-statement
    templateId: Optional[str] = None
    language: str = "zh-CN"
    options: dict = {}


class ExtractUploadResponse(BaseModel):
    taskId: str
    type: str
    fields: dict  # 字段名 → ExtractField
    suggestions: dict
    meta: AIMeta


class ExtractBatchUploadRequest(BaseModel):
    fileIds: list[str]  # 最多 100
    type: str = "invoice"
    templateId: Optional[str] = None


class ExtractBatchUploadResponse(BaseModel):
    batchId: str
    total: int
    streamUrl: str


class ExtractApplyRequest(BaseModel):
    taskId: str
    type: str
    originalFields: dict
    correctedFields: dict
    action: str = "save-to-form"  # save-to-form | discard | re-extract


class ExtractApplyResponse(BaseModel):
    taskId: str
    appliedToForm: bool
    invoiceId: Optional[int] = None


# ============================================================
# 6.2 风险识别
# ============================================================
class RiskScanRequest(BaseModel):
    objectType: str  # project | contract | expense | voucher
    objectId: int
    scanTypes: Optional[list[str]] = None
    options: dict = {}


class RiskWarning(BaseModel):
    id: str
    level: str  # high | medium | low
    type: str
    title: str
    description: str
    suggestion: str
    confidence: int
    dataPoints: dict
    createdAt: str


class RiskSuggestion(BaseModel):
    id: str
    title: str
    description: str
    action: dict
    confidence: int


class RiskSimilarObject(BaseModel):
    objectType: str
    objectId: int
    name: str
    healthScore: int
    delayDays: int
    overBudget: float


class RiskScanResponse(BaseModel):
    objectType: str
    objectId: int
    overallScore: int
    riskLevel: str
    dimensions: dict
    warnings: list[RiskWarning]
    suggestions: list[RiskSuggestion]
    similarObjects: list[RiskSimilarObject]
    meta: AIMeta


class RiskWarningsRequest(BaseModel):
    objectType: str
    objectId: int
    onlyActive: bool = True


class RiskWarningsResponse(BaseModel):
    warnings: list[RiskWarning]
    lastScanAt: Optional[str] = None
    stale: bool = False


class RiskDismissRequest(BaseModel):
    warningId: str
    action: str  # dismiss | accept | fix
    remark: Optional[str] = None


# ============================================================
# 6.3 智能问答
# ============================================================
class AskRequest(BaseModel):
    question: str
    context: dict = {}
    options: dict = {}  # stream: true | returnChart: true | maxSources: 5


class AskSource(BaseModel):
    type: str  # report | record | doc
    id: str
    title: str
    url: Optional[str] = None
    snippet: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    answerType: str  # data | doc | chart | draft
    data: dict
    chart: Optional[dict] = None
    sources: list[AskSource] = []
    conversationId: str
    messageId: str
    meta: AIMeta


class AskFeedbackRequest(BaseModel):
    messageId: str
    rating: str  # up | down
    reason: Optional[str] = None
    comment: Optional[str] = None


class AskSuggestionsRequest(BaseModel):
    page: str = "dashboard"
    limit: int = 5


class AskSuggestionsResponse(BaseModel):
    suggestions: list[dict]


# ============================================================
# 6.4 AI 提醒
# ============================================================
class AlertItem(BaseModel):
    id: str
    level: str  # high | medium | low
    type: str
    title: str
    summary: str
    actionUrl: Optional[str] = None
    actionLabel: Optional[str] = None
    createdAt: str


class AlertTodayRequest(BaseModel):
    limit: int = 3


class AlertTodayResponse(BaseModel):
    total: int
    items: list[AlertItem]


class AlertDismissRequest(BaseModel):
    alertId: str
    snoozeHours: int = 24


# ============================================================
# 6.5 AI 任务中心
# ============================================================
class TaskItem(BaseModel):
    id: str
    type: str
    name: Optional[str] = None
    status: str
    progress: float
    doneCount: int = 0
    totalCount: int = 0
    startedAt: Optional[str] = None
    finishedAt: Optional[str] = None
    estimatedRemainingSec: Optional[int] = None


class TaskListRequest(BaseModel):
    page: int = 1
    pageSize: int = Field(default=20, le=100)
    status: str = "all"  # running | done | failed | all
    type: str = "all"


class TaskListResponse(BaseModel):
    list: list[TaskItem]
    total: int
    page: int
    pageSize: int


class TaskCancelRequest(BaseModel):
    taskId: str


# ============================================================
# 6.7 反馈中心
# ============================================================
class FeedbackSubmitRequest(BaseModel):
    targetType: str  # extract | risk | ask | generate | match
    targetId: str
    rating: str  # up | down
    category: Optional[str] = None
    comment: Optional[str] = None
    tags: list[str] = []


# ============================================================
# 6.6 模型管理
# ============================================================
class ModelItem(BaseModel):
    id: str
    name: str
    type: str  # ocr | llm | risk
    status: str  # healthy | degraded | down | disabled
    version: str
    metrics: dict
    config: dict
    costPerCallCents: int
    monthlyUsage: int


class ModelListResponse(BaseModel):
    models: list[ModelItem]


class ModelConfigRequest(BaseModel):
    modelId: str
    config: dict
    enabled: bool = True


# ============================================================
# 全局 SSE
# ============================================================
class StreamEvent(BaseModel):
    """SSE 事件结构（参考 AI-API.md §4）"""
    event: str
    data: dict
