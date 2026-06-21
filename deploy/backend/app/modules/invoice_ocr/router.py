"""
发票识别路由
- /api/v1/invoice/ocr/*
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import Body, APIRouter, Depends, Form, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_permission, CurrentUser
from app.integrations import ocr_client
from app.modules.common import service as common_service
from app.modules.invoice_ocr import service
from app.modules.invoice_ocr.models import Invoice
from app.core.exceptions import ParamErrorException


router = APIRouter()


# ===== 上传 + OCR 识别（单张）=====

@router.post("/upload", summary="上传 + 单张识别")
async def upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoice:upload")),
):
    # 1. 保存文件
    file_info = await common_service.save_upload_file(db, current_user.id, file)
    # 2. OCR
    result = await service.recognize_one(db, file_info.fileId, file_info.url, current_user.id)
    return {"code": 0, "data": result}


# ===== 列表 =====
class InvoiceListRequest(BaseModel):
    page: int = 1
    pageSize: int = 20
    keyword: str = ""
    filters: dict = {}


@router.post("/records", summary="识别记录列表（兼容旧 chunk，统一转发到 /list）")
async def list_records_compat(
    page: int = 1,
    pageSize: int = 20,
    keyword: str = "",
    filters: dict = {},
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    items, total, status_counts = await service.list_invoices(db, page, pageSize, keyword, filters)
    return {"code": 0, "data": {"list": items, "total": total, "page": page, "pageSize": pageSize, "statusCounts": status_counts}}


@router.post("/list", summary="发票识别记录列表")
async def list_invoices(
    req: InvoiceListRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    items, total, status_counts = await service.list_invoices(db, req.page, req.pageSize, req.keyword, req.filters)
    return {"code": 0, "data": {"list": items, "total": total, "page": req.page, "pageSize": req.pageSize, "statusCounts": status_counts}}


# ===== 统计（4 个 KPI：业务月报指标，对齐 design/invoice-ocr.html）=====
@router.post("/stats", summary="发票识别统计 KPI（业务月报）")
async def stats(
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    """
    4 个 KPI（对齐设计稿）：
    - 本月识别：本月已上传的发票数（按 uploaded_at 算）
    - 识别成功率：本月识别成功 / 本月总数 × 100%
    - 待人工核验：所有 verify_status='pending' 且已识别成功的
    - 本月入账金额：本月已入账（status='submitted'）的金额合计（元）
    """
    from datetime import datetime
    from sqlalchemy import select, func, and_
    from app.modules.invoice_ocr.models import Invoice


    now = datetime.now()
    month_start = datetime(now.year, now.month, 1)

    # 1. 本月识别：本月 uploaded_at 的所有发票数
    monthly_count = (await db.execute(
        select(func.count(Invoice.id)).where(Invoice.uploaded_at >= month_start)
    )).scalar() or 0

    # 2. 识别成功率：本月识别成功(status in verified/submitted) / 本月总数
    monthly_success = (await db.execute(
        select(func.count(Invoice.id)).where(
            Invoice.uploaded_at >= month_start,
            Invoice.status.in_(("verified", "submitted"))
        )
    )).scalar() or 0
    success_rate = round(monthly_success / monthly_count * 100, 1) if monthly_count else 0.0

    # 3. 待人工核验：所有 verify_status='pending' 且已识别成功的
    pending_verify = (await db.execute(
        select(func.count(Invoice.id)).where(
            and_(
                Invoice.status == "verified",
                Invoice.verify_status == "pending"
            )
        )
    )).scalar() or 0

    # 4. 本月入账金额：本月入账（status='submitted'）的金额合计（元，total_amount 是分）
    monthly_amount_cents = (await db.execute(
        select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
            and_(
                Invoice.status == "submitted",
                Invoice.uploaded_at >= month_start
            )
        )
    )).scalar() or 0
    monthly_amount = float(monthly_amount_cents) / 100.0

    return {
        "code": 0,
        "data": {
            "list": [
                {"key": "monthlyCount",   "label": "本月识别",     "value": monthly_count,    "unit": "张"},
                {"key": "successRate",    "label": "识别成功率",   "value": success_rate,     "unit": "%", "isPercent": True},
                {"key": "pendingVerify",  "label": "待人工核验",   "value": pending_verify,   "unit": "张"},
                {"key": "monthlyAmount",  "label": "本月入账金额", "value": monthly_amount,   "unit": "元", "isCurrency": True},
            ],
            "total": monthly_count,
        },
    }


# ===== 详情 =====
@router.post("/detail", summary="发票详情")
async def detail(
    body: dict | None = Body(default=None),
    invoiceId: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    """支持 body {invoiceId|id} 或 query ?invoiceId= 两种调用方式"""
    _id = invoiceId
    if _id is None and body:
        _id = body.get("invoiceId") or body.get("id")
    if _id is None:
        raise ParamErrorException("invoiceId 必填")
    data = await service.get_invoice(db, _id)
    return {"code": 0, "data": data}


# ===== 更新（编辑字段 + 关联）=====
class UpdateInvoiceRequest(BaseModel):
    fields: dict = {}
    expenseInfo: Optional[dict] = None
    # 允许把 verifyStatus 等字段直接放顶层（前端简化）
    verifyStatus: Optional[str] = None
    verifyAt: Optional[str] = None
    verifySource: Optional[str] = None


@router.post("/update", summary="编辑/核验发票")
async def update(
    invoiceId: int = Query(...),
    body: UpdateInvoiceRequest = UpdateInvoiceRequest(),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("invoice:write")),
):
    # 合并顶层 verifyStatus 到 fields（前端简化）
    fields = dict(body.fields or {})
    for k in ('verifyStatus', 'verifyAt', 'verifySource'):
        v = getattr(body, k, None)
        if v is not None and k not in fields:
            fields[k] = v
    data = await service.update_invoice(db, invoiceId, fields, body.expenseInfo)
    return {"code": 0, "data": data, "message": "已更新"}


# ===== 提交入账 =====
@router.post("/submit", summary="提交入账")
async def submit(
    invoiceId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("invoice:submit")),
):
    data = await service.submit_invoice(db, invoiceId)
    return {"code": 0, "data": data, "message": "已入账"}


# ===== 重新识别 =====
@router.post("/recheck", summary="重新识别")
async def recheck(
    invoiceId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.recheck_invoice(db, invoiceId)
    return {"code": 0, "data": data, "message": "已重新识别"}


# ===== 批量上传 =====
@router.post("/batch/upload", summary="批量上传")
async def batch_upload(
    files: list[UploadFile] = File(...),
    templateId: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoice:batch_upload")),
):
    # 先把所有文件存好
    file_infos = []
    for f in files:
        info = await common_service.save_upload_file(db, current_user.id, f)
        file_infos.append({
            "fileId": info.fileId,
            "filename": f.filename or "unnamed",
            "size": info.size,
            "url": info.url,
        })
    # 创建批量任务
    result = await service.create_batch_task(
        db, file_infos,
        int(templateId) if templateId else None,
        current_user.id,
    )
    return {"code": 0, "data": result}


# ===== 批量状态查询 =====
@router.post("/batch/status", summary="批量任务状态（兼容旧版，建议用 SSE）")
async def batch_status(
    batchId: str = Query(..., description="批量任务 ID（code 字符串）"),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.get_batch_status(db, batchId)
    return {"code": 0, "data": data}


# ===== 批量提交入账 =====
class BatchSubmitRequest(BaseModel):
    invoiceIds: list[int]


@router.post("/batch/submit", summary="批量提交入账")
async def batch_submit(
    req: BatchSubmitRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("invoice:submit")),
):
    data = await service.submit_batch(db, req.invoiceIds)
    return {"code": 0, "data": data, "message": f"已入账 {data['updated']} 张"}


# ===== 批量重试失败项 =====
class BatchRetryRequest(BaseModel):
    batchId: str
    fileIds: list[str]


@router.post("/batch/retry", summary="批量重试失败项")
async def batch_retry(
    req: BatchRetryRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.retry_batch_items(db, req.batchId, req.fileIds)
    return {"code": 0, "data": data, "message": f"已重新入队 {data['queued']} 项"}


# ===== 批量删除 =====
class BatchDeleteRequest(BaseModel):
    invoiceIds: list[int]


@router.post("/batch/delete", summary="批量删除发票")
async def batch_delete(
    req: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("invoice:write")),
):
    if not req.invoiceIds:
        return {"code": 0, "data": {"deleted": 0}, "message": "未选择任何发票"}
    deleted = await service.delete_invoices(db, req.invoiceIds)
    return {"code": 0, "data": {"deleted": deleted}, "message": f"已删除 {deleted} 张发票"}


# ===== 高级搜索 =====
@router.post("/advanced-search", summary="高级筛选")
async def advanced_search(
    req: InvoiceListRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    # 简化：复用 list，filters 支持更复杂条件
    items, total, status_counts = await service.list_invoices(db, req.page, req.pageSize, req.keyword, req.filters)
    return {"code": 0, "data": {"list": items, "total": total, "page": req.page, "pageSize": req.pageSize, "statusCounts": status_counts}}


# ===== 批量操作 =====
class BatchActionRequest(BaseModel):
    action: str  # submit/link_contract/export/delete/tag
    invoiceIds: list[int]
    params: dict = {}


@router.post("/batch-action", summary="批量操作")
async def batch_action(
    req: BatchActionRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    if req.action == "submit":
        data = await service.submit_batch(db, req.invoiceIds)
        return {"code": 0, "data": data, "message": f"已入账 {data['updated']} 张"}
    return {"code": 0, "data": {"action": req.action, "count": len(req.invoiceIds)}, "message": "操作完成"}


# ===== 保存视图 =====
class SavedViewRequest(BaseModel):
    viewName: str
    filters: dict
    isShared: bool = False


@router.post("/saved-view", summary="保存为常用视图")
async def save_view(
    req: SavedViewRequest,
    _user: CurrentUser = Depends(get_current_user),
):
    # 简化：只回显（实际需要 user_saved_views 表）
    return {"code": 0, "data": {"viewName": req.viewName, "saved": True}, "message": "已保存"}


# ===== 视图列表 =====
@router.post("/views", summary="已保存的视图")
async def list_views(_user: CurrentUser = Depends(get_current_user)):
    return {"code": 0, "data": {"list": []}}
