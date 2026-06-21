"""
报销中心 Schemas
"""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ===== 列表 =====
class ReimburseListRequest(BaseModel):
    page: int = 1
    pageSize: int = Field(default=20, le=100)
    keyword: Optional[str] = None
    filters: dict = {}


# ===== 模板 =====
class ReimburseTemplate(BaseModel):
    code: str
    name: str
    type: str  # general / travel / hospitality / marketing / custom
    icon: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    # JSON 模板定义（用于 PDF 渲染 / 打印 / 前端表单）
    schema_: Optional[dict] = Field(default=None, alias="schema")
    builtin: bool = True


# ===== 创建 / 编辑 =====
class ReimburseDetailIn(BaseModel):
    expenseId: int
    amount: Optional[int] = None  # 不传则用费用原金额
    remark: Optional[str] = None


class ReimburseCreate(BaseModel):
    templateType: str = "general"
    title: Optional[str] = None
    applicantId: Optional[int] = None
    departmentId: Optional[int] = None
    expenseIds: List[int] = []                    # 关联的销售费用 ID 列表
    expenseDate: Optional[date] = None
    remark: Optional[str] = None
    aiDescription: Optional[str] = None


class ReimburseUpdate(BaseModel):
    formId: int
    title: Optional[str] = None
    templateType: Optional[str] = None
    expenseIds: Optional[List[int]] = None
    expenseDate: Optional[date] = None
    remark: Optional[str] = None
    aiDescription: Optional[str] = None


# ===== 回填实际报销结果 =====
class ReimburseFillback(BaseModel):
    formId: int
    actualAmount: int                                # 实际报销金额（分）
    paymentDate: Optional[date] = None
    voucherNo: Optional[str] = None
    remark: Optional[str] = None
    # 每个明细的实际分摊金额（按 expenseId -> 分）
    detailAmounts: Optional[dict] = None


# ===== 删除 =====
class ReimburseDelete(BaseModel):
    formId: int


# ===== 模板 AI 生成说明 / 风险检测 =====
class AiDescriptionRequest(BaseModel):
    formId: Optional[int] = None
    expenseIds: List[int] = []


class AiRiskRequest(BaseModel):
    formId: Optional[int] = None
    expenseIds: List[int] = []


# ===== 响应模型 =====
class ReimburseDetailOut(BaseModel):
    id: int
    expenseId: int
    expenseCode: Optional[str] = None
    expenseType: Optional[str] = None
    expenseDate: Optional[date] = None
    clientName: Optional[str] = None
    projectName: Optional[str] = None
    title: Optional[str] = None
    amount: int
    reimbursedAmount: int = 0
    remark: Optional[str] = None


class ReimburseFormOut(BaseModel):
    formId: int
    formNo: str
    templateType: str
    title: str
    applicant: Optional[dict] = None
    department: Optional[dict] = None
    totalAmount: int
    actualAmount: int
    currency: str = "CNY"
    status: str
    statusLabel: str = ""
    expenseDate: Optional[date] = None
    paymentDate: Optional[date] = None
    voucherNo: Optional[str] = None
    detailCount: int = 0
    aiDescription: Optional[str] = None
    aiRiskFlag: Optional[str] = None
    aiRiskReason: Optional[str] = None
    remark: Optional[str] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None
    details: List[ReimburseDetailOut] = []



# ===== 模板自定义 =====
class ReimburseTemplateOut(BaseModel):
    id: Optional[int] = None
    code: str
    name: str
    type: str
    icon: str = "📋"
    color: str = "#4F6BFF"
    description: Optional[str] = None
    schema: dict
    isSystem: bool = False
    createdBy: Optional[int] = None
    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None


class ReimburseTemplateCreate(BaseModel):
    code: Optional[str] = None   # 不传则自动生成
    name: str
    type: str = "custom"
    icon: str = "📋"
    color: str = "#4F6BFF"
    description: Optional[str] = None
    schema: dict


class ReimburseTemplateUpdate(BaseModel):
    templateId: int
    name: Optional[str] = None
    type: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    schema: Optional[dict] = None


class ReimburseTemplateDelete(BaseModel):
    templateId: int


class ReimburseTemplateClone(BaseModel):
    code: str  # 要复制的内置模板 code


class ReimburseTemplateRecognizeResp(BaseModel):
    """上传识别响应"""
    detectedFields: list = []      # 检测到的字段 [{key,label,type}]
    suggestedSchema: dict          # 推荐 schema
    textPreview: str = ""         # 文本预览
    confidence: float = 0.0        # 识别置信度
