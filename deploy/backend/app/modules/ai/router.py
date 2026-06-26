"""
AI 平台路由
- /api/v1/ai/*  (AI-API.md §5)
- 18 个必出接口 + 1 个全局 SSE
"""
from fastapi import APIRouter, Depends, Query, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse

from app.core.database import get_db
from app.core.security import get_current_user, require_permission, CurrentUser
from app.core.sse import event_stream
from app.modules.ai import service
from app.modules.ai import schemas as sch


router = APIRouter()


# ============================================================
# 6.1 字段抽取
# ============================================================

@router.post("/extract/upload", summary="单张字段抽取（同步 < 3s）")
async def extract_upload(
    req: sch.ExtractUploadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:extract")),
):
    data = await service.extract_upload(db, req, current_user.id)
    return {"code": 0, "data": data}


@router.post("/extract/batch/upload", summary="批量字段抽取（异步 SSE）")
async def extract_batch_upload(
    req: sch.ExtractBatchUploadRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:extract")),
):
    data = await service.extract_batch_upload(db, req, current_user.id)
    return {"code": 0, "data": data}


@router.get("/extract/batch/stream", summary="批量抽取 SSE 流")
async def extract_batch_stream(
    batchId: str = Query(...),
    token: str = Query(...),
):
    """SSE 通道 /api/v1/ai/extract/batch/stream?batchId=...&token=..."""
    from app.core.security import decode_token
    from app.core.exceptions import UnauthorizedException
    try:
        decode_token(token)
    except Exception:
        raise UnauthorizedException("Token 无效")
    return StreamingResponse(
        event_stream(f"ai:extract:{batchId}"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/extract/apply", summary="采纳 AI 抽取结果（数据回流）")
async def extract_apply(
    req: sch.ExtractApplyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    data = await service.extract_apply(db, req, current_user.id)
    return {"code": 0, "data": data}


# ============================================================
# 6.2 风险识别
# ============================================================

@router.post("/risk/scan", summary="单条风险扫描")
async def risk_scan(
    req: sch.RiskScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:risk.scan")),
):
    data = await service.risk_scan(db, req, current_user.id)
    return {"code": 0, "data": data}


@router.post("/risk/warnings", summary="拉取某对象的所有风险")
async def risk_warnings(
    req: sch.RiskWarningsRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.risk_warnings(db, req)
    return {"code": 0, "data": data}


@router.post("/risk/dismiss", summary="忽略/采纳风险")
async def risk_dismiss(
    req: sch.RiskDismissRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    data = await service.risk_dismiss(db, req, current_user.id)
    return {"code": 0, "data": data}


# ============================================================
# 6.3 智能问答
# ============================================================

@router.post("/ask/ask", summary="自然语言提问")
async def ask(
    req: sch.AskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("ai:ask")),
):
    data = await service.ask(db, req, current_user.id)
    return {"code": 0, "data": data}


@router.post("/ask/feedback", summary="问答反馈（👍/👎）")
async def ask_feedback(
    req: sch.AskFeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    data = await service.ask_feedback(db, req, current_user.id)
    return {"code": 0, "data": data}


@router.post("/ask/suggestions", summary="推荐问题")
async def ask_suggestions(
    req: sch.AskSuggestionsRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.ask_suggestions(db, req)
    return {"code": 0, "data": data}


# ============================================================
# 6.4 AI 提醒
# ============================================================

@router.post("/alert/today", summary="今日 AI 助手提醒")
async def alert_today(
    req: sch.AlertTodayRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    data = await service.alert_today(db, req, current_user.id)
    return {"code": 0, "data": data}


@router.post("/alert/dismiss", summary="关闭 / 延后提醒")
async def alert_dismiss(
    req: sch.AlertDismissRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    data = await service.alert_dismiss(db, req, current_user.id)
    return {"code": 0, "data": data}


# ============================================================
# 6.5 AI 任务中心
# ============================================================

@router.post("/task/list", summary="AI 任务列表")
async def task_list(
    req: sch.TaskListRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.task_list(db, req)
    return {"code": 0, "data": data}


@router.post("/task/cancel", summary="取消 AI 任务")
async def task_cancel(
    req: sch.TaskCancelRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.task_cancel(db, req)
    return {"code": 0, "data": data}


# ============================================================
# 6.6 模型管理（仅管理员）
# ============================================================

@router.post("/model/list", summary="AI 模型列表")
async def model_list(
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("ai:model.manage")),
):
    data = await service.model_list(db)
    return {"code": 0, "data": data}


@router.post("/model/config", summary="配置 AI 模型")
async def model_config(
    req: sch.ModelConfigRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("ai:model.manage")),
):
    data = await service.model_config(db, req)
    return {"code": 0, "data": data}


@router.post("/model/test", summary="测试 LLM 连通性")
async def model_test(
    req: dict = Body(...),
    _user: CurrentUser = Depends(get_current_user),
):
    """发一个最小 chat/completions 请求验证 baseUrl + apiKey + model 是否可用"""
    data = await service.model_test_connection(
        base_url=req.get("baseUrl", ""),
        api_key=req.get("apiKey", ""),
        model=req.get("model", ""),
    )
    return {"code": 0 if data.get("ok") else 1, "message": data.get("message"), "data": data}


# ============================================================
# 6.7 反馈中心
# ============================================================

@router.post("/feedback/submit", summary="提交 AI 反馈")
async def feedback_submit(
    req: sch.FeedbackSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    data = await service.feedback_submit(db, req, current_user.id)
    return {"code": 0, "data": data}


# ============================================================
# 6.8 全局 SSE 入口
# ============================================================

@router.get("/stream", summary="全局 SSE 入口（多事件流）")
async def global_stream(
    token: str = Query(...),
    topics: str = Query("extract,risk,alert,ask", description="订阅主题，逗号分隔"),
):
    """?token=xxx&topics=extract,risk,alert,ask"""
    from app.core.security import decode_token
    from app.core.exceptions import UnauthorizedException
    try:
        decode_token(token)
    except Exception:
        raise UnauthorizedException("Token 无效")

    # 多 topic 合并到一个 channel
    return StreamingResponse(
        event_stream(f"ai:global:{topics}"),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
