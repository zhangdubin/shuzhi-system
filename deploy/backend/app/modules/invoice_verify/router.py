"""
发票查验路由
- /api/v1/invoice/verify/*
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_permission, CurrentUser
from app.modules.invoice_verify import service


router = APIRouter()


class VerifySingleRequest(BaseModel):
    invoiceCode: str = ""  # 兼容空（电子发票无发票代码）
    invoiceNo: str
    issueDate: str
    totalAmount: float
    verifyCode: Optional[str] = None
    # 可选：从识别记录选的话带上，便于后续关联报销/凭证
    invoiceId: Optional[int] = None


@router.post("/single", summary="单张验真")
async def verify_single(
    req: VerifySingleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoice:verify")),
):
    data = await service.verify_single(
        db, req.invoiceCode, req.invoiceNo, req.issueDate, req.totalAmount, req.verifyCode, current_user.id, req.invoiceId,
    )
    return {"code": 0, "data": data}


class VerifyBatchRequest(BaseModel):
    invoices: list[dict]


@router.post("/batch", summary="批量验真（最多 50 张）")
async def verify_batch(
    req: VerifyBatchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoice:verify")),
):
    data = await service.verify_batch(db, req.invoices, current_user.id)
    return {"code": 0, "data": data}


class VerifyListRequest(BaseModel):
    page: int = 1
    pageSize: int = 20
    filters: dict = {}


@router.post("/list", summary="查验记录列表")
async def list_records(
    req: VerifyListRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    items, total = await service.list_verify_records(db, req.page, req.pageSize, req.filters)
    return {"code": 0, "data": {"list": items, "total": total, "page": req.page, "pageSize": req.pageSize}}


@router.post("/certificate", summary="下载查验凭证")
async def certificate(
    verifyId: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.get_certificate(db, verifyId)
    return {"code": 0, "data": data}


# ===== 健康检查 + 配置 =====
@router.get("/health", summary="查验服务健康检查")
async def verify_health():
    """探测诺诺发票查验接口可用性 + 当前模式"""
    from app.integrations import nuonuo
    from app.config import settings
    h = await nuonuo.health_check()
    return {
        "code": 0,
        "data": {
            "mode": settings.NUONUO_MODE,             # real | mock
            "configured": bool(settings.NUONUO_API_KEY),
            "useSandbox": settings.NUONUO_USE_SANDBOX,
            "apiUrl": settings.NUONUO_API_URL,
            "status": h.get("status", "unknown"),     # mock | reachable | degraded | down
            "message": h.get("error") or _health_msg(h.get("status")),
        },
    }


def _health_msg(status: str) -> str:
    return {
        "mock": "未配置 API Key，当前使用本地 mock 数据；不影响功能演示",
        "reachable": "国税接口已连接，可正常查验",
        "degraded": "国税接口响应异常，自动回退 mock",
        "down": "国税接口不可达，请检查网络或凭据",
    }.get(status, f"未知状态: {status}")


@router.get("/config", summary="查看当前查验服务配置（脱敏）")
async def verify_config():
    """脱敏返回当前环境配置，方便用户在 UI 上确认配置是否正确"""
    from app.config import settings
    def mask(s: str) -> str:
        if not s:
            return ""
        if len(s) <= 8:
            return s[:2] + "***"
        return s[:4] + "***" + s[-4:]
    return {
        "code": 0,
        "data": {
            "mode": settings.NUONUO_MODE,
            "apiUrl": settings.NUONUO_API_URL,
            "useSandbox": settings.NUONUO_USE_SANDBOX,
            "appKeyMasked": mask(settings.NUONUO_API_KEY),
            "appSecretMasked": mask(settings.NUONUO_API_SECRET),
            "accessTokenMasked": mask(settings.NUONUO_API_TOKEN),
            "configured": bool(settings.NUONUO_API_KEY),
            "configSource": ".env (SHUZHI_NUONUO_* / NUONUO_*)",
            "guide": "如需切换为真实国税接口：编辑 backend/.env 填入 NUONUO_API_KEY/SECRET/TOKEN 并设置 NUONUO_MODE=real",
        },
    }


class VerifyMarkRequest(BaseModel):
    verifyId: str
    action: str  # mark/isolate/report
    comment: Optional[str] = None


@router.post("/mark", summary="标记风险发票")
async def mark(
    req: VerifyMarkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    data = await service.mark_risk(db, req.verifyId, req.action, req.comment, current_user.id)
    return {"code": 0, "data": data, "message": "已标记"}
