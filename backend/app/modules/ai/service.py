"""
AI 平台服务层
实现 AI-API.md §6 的 18 个必出接口
"""
import asyncio
import json
import random
import string
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, or_, select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException
from app.core.sse import publish_event
from app.core import cache as cache_mod
from app.core.cache import invalidate
from app.config import settings
from app.modules.ai import ai_client
from app.modules.ai.models import AITask, AIFeedback, AIAlert


# ============================================================
# 工具
# ============================================================
def _gen_task_id() -> str:
    return f"task_{uuid.uuid4().hex[:10]}"


def _gen_alert_id() -> str:
    return f"alert_{uuid.uuid4().hex[:8]}"


async def _record_ai_task(
    db: AsyncSession,
    *,
    task_id: str,
    type: str,
    sub_type: Optional[str] = None,
    name: Optional[str] = None,
    input_data: dict,
    output_data: Optional[dict] = None,
    error: Optional[dict] = None,
    status: str = "done",
    cost_cents: int = 0,
    model: Optional[str] = None,
    model_version: Optional[str] = None,
    confidence: Optional[float] = None,
    total_count: int = 0,
    done_count: int = 0,
    failed_count: int = 0,
    duration_ms: int = 0,
    created_by: int = 0,
    source: str = "web",
) -> AITask:
    """记录 AI 任务到数据库"""
    now = datetime.utcnow()
    task = AITask(
        task_id=task_id, tenant_id=1, type=type, sub_type=sub_type, name=name,
        status=status, input=input_data, output=output_data, error=error,
        cost_cents=cost_cents, model=model, model_version=model_version,
        confidence=confidence,
        total_count=total_count, done_count=done_count, failed_count=failed_count,
        created_by=created_by, source=source,
        started_at=now, finished_at=now if status in ("done", "failed") else None,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


# ============================================================
# 6.1 字段抽取
# ============================================================

async def extract_upload(
    db: AsyncSession, req, user_id: int
) -> dict:
    """单张抽取（同步）"""
    result = await ai_client.ocr_extract(
        req.fileId, req.fileUrl, req.type, req.templateId, req.language, req.options
    )
    # 记录任务
    await _record_ai_task(
        db,
        task_id=result["taskId"],
        type="extract",
        sub_type=f"extract.{req.type}",
        input_data=req.model_dump(),
        output_data={"fields": result["fields"], "suggestions": result["suggestions"]},
        cost_cents=result["meta"]["costCents"],
        model=result["meta"]["model"],
        model_version=result["meta"]["version"],
        confidence=result["meta"]["confidence"],
        duration_ms=result["meta"]["durationMs"],
        created_by=user_id,
    )
    return result


async def extract_batch_upload(db: AsyncSession, req, user_id: int) -> dict:
    """批量抽取（异步，触发后台 SSE 推送）"""
    batch_id = f"batch_{uuid.uuid4().hex[:10]}"
    await _record_ai_task(
        db,
        task_id=batch_id,
        type="extract",
        sub_type=f"extract.{req.type}.batch",
        name=f"批量抽取 {len(req.fileIds)} 张",
        input_data=req.model_dump(),
        status="running",
        total_count=len(req.fileIds),
        created_by=user_id,
    )
    # 异步后台处理
    asyncio.create_task(
        _process_extract_batch(batch_id, req.fileIds, req.type, user_id)
    )
    return {
        "batchId": batch_id,
        "total": len(req.fileIds),
        "streamUrl": f"/api/v1/ai/stream?topics=extract.{batch_id}&token=...",
    }


async def _process_extract_batch(batch_id: str, file_ids: list[str], type: str, user_id: int):
    """后台处理批量抽取 + SSE 推送"""
    from app.core.database import AsyncSessionLocal
    success = warning = failed = 0

    # 连接事件
    await publish_event(
        f"ai:extract:{batch_id}", "connected", {"batchId": batch_id, "total": len(file_ids)}
    )

    for i, fid in enumerate(file_ids, start=1):
        try:
            result = await ai_client.ocr_extract(fid, f"https://cdn.example.com/{fid}", type)
            fields = result["fields"]
            confidences = [v.get("confidence", 0) for v in fields.values() if isinstance(v, dict)]
            avg_conf = sum(confidences) / len(confidences) if confidences else 0
            needs_review = any(
                isinstance(v, dict) and v.get("confidence", 100) < 70
                for v in fields.values()
            )

            # 推送 extracted 事件
            await publish_event(
                f"ai:extract:{batch_id}", "extracted",
                {"fileId": fid, "taskId": result["taskId"], "fields": fields, "needsReview": needs_review}
            )

            if needs_review:
                warning += 1
            else:
                success += 1
        except Exception as e:
            failed += 1
            await publish_event(
                f"ai:extract:{batch_id}", "error",
                {"code": 5102, "message": str(e), "fileId": fid}
            )

        # 推送 progress
        await publish_event(
            f"ai:extract:{batch_id}", "progress",
            {
                "batchId": batch_id,
                "done": i, "total": len(file_ids),
                "percent": round(i / len(file_ids) * 100, 1),
                "stage": "识别中",
            }
        )
        # 推送 summary
        await publish_event(
            f"ai:extract:{batch_id}", "summary",
            {
                "total": len(file_ids),
                "success": success, "warning": warning, "failed": failed,
            }
        )
        await asyncio.sleep(0.05)  # 避免 SSE 过频

    # 完成
    await publish_event(
        f"ai:extract:{batch_id}", "completed",
        {
            "batchId": batch_id,
            "finishedAt": datetime.utcnow().isoformat(),
            "costCents": len(file_ids) * 0,  # paddleocr 免费
        }
    )

    # 更新任务状态
    async with AsyncSessionLocal() as db:
        task = (await db.execute(
            select(AITask).where(AITask.task_id == batch_id)
        )).scalar_one_or_none()
        if task:
            task.status = "done"
            task.done_count = success
            task.failed_count = failed
            task.finished_at = datetime.utcnow()
            await db.commit()


async def extract_apply(
    db: AsyncSession, req, user_id: int
) -> dict:
    """采纳抽取结果（数据回流）"""
    # 找到原 task
    task = (await db.execute(
        select(AITask).where(AITask.task_id == req.taskId)
    )).scalar_one_or_none()
    if not task:
        raise NotFoundException(f"任务不存在：{req.taskId}")

    # 写入 feedback（数据回流）
    diff = {}
    for k, new_v in (req.correctedFields or {}).items():
        old = (req.originalFields or {}).get(k, {})
        if isinstance(old, dict) and old.get("value") != new_v.get("value"):
            diff[k] = {"old": old.get("value"), "new": new_v.get("value")}

    if diff:
        fb = AIFeedback(
            tenant_id=1, target_type="extract", target_id=req.taskId,
            user_id=user_id, rating="up" if not diff else "down",
            category="inaccurate" if diff else "accurate",
            comment=json.dumps(diff, ensure_ascii=False),
            tags=["extract.apply"],
        )
        db.add(fb)
        await db.commit()

    return {
        "taskId": req.taskId,
        "appliedToForm": req.action == "save-to-form",
        "invoiceId": None,  # 真实场景应该返回新建的发票 id
    }


# ============================================================
# 6.2 风险扫描
# ============================================================

async def risk_scan(db: AsyncSession, req, user_id: int) -> dict:
    result = await ai_client.risk_scan(req.objectType, req.objectId)
    await _record_ai_task(
        db,
        task_id=f"risk_{uuid.uuid4().hex[:10]}",
        type="risk",
        sub_type=f"risk.scan.{req.objectType}",
        name=f"风险扫描 {req.objectType}#{req.objectId}",
        input_data=req.model_dump(),
        output_data={
            "overallScore": result["overallScore"],
            "riskLevel": result["riskLevel"],
            "warningsCount": len(result["warnings"]),
        },
        cost_cents=result["meta"]["costCents"],
        model=result["meta"]["model"],
        model_version=result["meta"]["version"],
        confidence=result["overallScore"],
        duration_ms=result["meta"]["durationMs"],
        created_by=user_id,
    )
    return result


async def risk_warnings(db: AsyncSession, req) -> dict:
    """拉取某对象的所有风险（mock：从最近一次扫描记录里拿）"""
    task = (await db.execute(
        select(AITask)
        .where(
            AITask.sub_type == f"risk.scan.{req.objectType}",
            AITask.input["objectId"].astext == str(req.objectId),
        )
        .order_by(AITask.created_at.desc())
        .limit(1)
    )).scalar_one_or_none()

    if not task or not task.output:
        # 跑一次新扫描
        scan_result = await ai_client.risk_scan(req.objectType, req.objectId)
        warnings = scan_result["warnings"]
        last_scan_at = datetime.utcnow().isoformat()
    else:
        warnings = task.output.get("warnings", [])
        last_scan_at = task.created_at.isoformat() if task.created_at else None

    # 过滤"已忽略"
    if req.onlyActive:
        warnings = [w for w in warnings if w.get("level") in ("high", "medium")]

    stale = True
    if task and task.created_at:
        age_hours = (datetime.utcnow() - task.created_at).total_seconds() / 3600
        stale = age_hours > 24

    return {"warnings": warnings, "lastScanAt": last_scan_at, "stale": stale}


async def risk_dismiss(db: AsyncSession, req, user_id: int) -> dict:
    """忽略/采纳风险（写 feedback 表）"""
    fb = AIFeedback(
        tenant_id=1, target_type="risk", target_id=req.warningId,
        user_id=user_id, rating="up" if req.action == "fix" else "down",
        category="dismissed" if req.action == "dismiss" else "accepted",
        comment=req.remark,
    )
    db.add(fb)
    await db.commit()
    return {"warningId": req.warningId, "action": req.action, "dismissed": True}


# ============================================================
# 6.3 智能问答
# ============================================================

async def ask(db: AsyncSession, req, user_id: int) -> dict:
    """问答（mock 走数据库）"""
    result = await ai_client.llm_ask(req.question, req.context)
    await _record_ai_task(
        db,
        task_id=result["messageId"],
        type="ask",
        sub_type="ask.qa",
        input_data=req.model_dump(),
        output_data={"answer": result["answer"], "answerType": result["answerType"]},
        cost_cents=result["meta"]["costCents"],
        model=result["meta"]["model"],
        confidence=85,  # mock
        duration_ms=result["meta"]["durationMs"],
        created_by=user_id,
    )
    return result


async def ask_feedback(db: AsyncSession, req, user_id: int) -> dict:
    fb = AIFeedback(
        tenant_id=1, target_type="ask", target_id=req.messageId,
        user_id=user_id, rating=req.rating,
        category=req.reason, comment=req.comment,
    )
    db.add(fb)
    await db.commit()
    return {"messageId": req.messageId, "feedbackSaved": True}


async def ask_suggestions(db: AsyncSession, req) -> dict:
    """推荐问题（按 page 路由推荐）"""
    base = {
        "dashboard": [
            {"text": "本月哪些回款逾期了？", "icon": "💰", "category": "risk"},
            {"text": "本周销售费用花了多少？", "icon": "📊", "category": "report"},
            {"text": "在建项目有哪些？", "icon": "📁", "category": "project"},
        ],
        "contract": [
            {"text": "本月新签了哪些合同？", "icon": "🤝", "category": "contract"},
            {"text": "快到期的合同有哪些？", "icon": "⏰", "category": "contract"},
        ],
        "expense": [
            {"text": "本季度销售费用汇总", "icon": "📊", "category": "report"},
            {"text": "差旅费用占比", "icon": "✈️", "category": "analysis"},
        ],
        "receivable": [
            {"text": "逾期超过 7 天的回款", "icon": "⚠️", "category": "risk"},
            {"text": "本月预计到账金额", "icon": "💵", "category": "forecast"},
        ],
        "project": [
            {"text": "进度落后的项目", "icon": "📉", "category": "risk"},
            {"text": "项目预算使用率 Top5", "icon": "💰", "category": "analysis"},
        ],
    }
    items = base.get(req.page, base["dashboard"])[:req.limit]
    return {"suggestions": items}


# ============================================================
# 6.4 AI 提醒
# ============================================================

async def alert_today(db: AsyncSession, req, user_id: int) -> dict:
    """今日提醒（从 ai_alerts 表查）"""
    rows = (await db.execute(
        select(AIAlert)
        .where(
            AIAlert.status == "unread",
            or_(AIAlert.user_id == user_id, AIAlert.user_id.is_(None))
        )
        .order_by(AIAlert.level.asc(), AIAlert.created_at.desc())  # high 排前
        .limit(req.limit)
    )).scalars().all()

    total = (await db.execute(
        select(func.count()).select_from(AIAlert)
        .where(AIAlert.status == "unread", or_(AIAlert.user_id == user_id, AIAlert.user_id.is_(None)))
    )).scalar() or 0

    items = [
        {
            "id": r.id,  # 数据库主键
            "level": r.level, "type": r.type,
            "title": r.title, "summary": r.summary or "",
            "actionUrl": r.action_url, "actionLabel": r.action_label or "查看",
            "createdAt": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
    return {"total": total, "items": items}


async def alert_dismiss(db: AsyncSession, req, user_id: int) -> dict:
    """关闭 / 延后提醒"""
    alert = (await db.execute(
        select(AIAlert).where(AIAlert.id == int(req.alertId.split("_")[-1] if "_" in req.alertId else req.alertId))
    )).scalar_one_or_none()
    if not alert:
        # 尝试按业务 ID 查
        alert = (await db.execute(
            select(AIAlert).where(AIAlert.title.contains(req.alertId))
        )).scalar_one_or_none()
    if alert:
        alert.status = "dismissed"
        alert.dismiss_remark = f"用户 {user_id} 已处理（snooze {req.snoozeHours}h）"
        if req.snoozeHours > 0:
            alert.snooze_until = datetime.utcnow() + timedelta(hours=req.snoozeHours)
        await db.commit()
        return {"alertId": req.alertId, "dismissed": True}
    return {"alertId": req.alertId, "dismissed": False, "note": "未找到对应记录"}


# ============================================================
# 6.5 AI 任务中心
# ============================================================

async def task_list(db: AsyncSession, req) -> dict:
    query = select(AITask)
    if req.status != "all":
        query = query.where(AITask.status == req.status)
    if req.type != "all":
        query = query.where(AITask.type == req.type)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = query.order_by(AITask.created_at.desc()).offset((req.page - 1) * req.pageSize).limit(req.pageSize)
    rows = (await db.execute(query)).scalars().all()

    items = [
        {
            "id": t.task_id, "type": t.type, "name": t.name,
            "status": t.status, "progress": float(t.progress or 0),
            "doneCount": t.done_count, "totalCount": t.total_count,
            "startedAt": t.started_at.isoformat() if t.started_at else None,
            "finishedAt": t.finished_at.isoformat() if t.finished_at else None,
            "estimatedRemainingSec": _estimate_remaining(t),
        }
        for t in rows
    ]
    return {"list": items, "total": total, "page": req.page, "pageSize": req.pageSize}


def _estimate_remaining(t: AITask) -> Optional[int]:
    if t.status not in ("running", "pending") or not t.total_count or not t.done_count:
        return None
    if not t.started_at:
        return None
    elapsed = (datetime.utcnow() - t.started_at).total_seconds()
    rate = t.done_count / max(elapsed, 0.001)
    if rate <= 0:
        return None
    return int((t.total_count - t.done_count) / rate)


async def task_cancel(db: AsyncSession, req) -> dict:
    task = (await db.execute(
        select(AITask).where(AITask.task_id == req.taskId)
    )).scalar_one_or_none()
    if not task:
        raise NotFoundException(f"任务不存在：{req.taskId}")
    if task.status in ("done", "failed", "cancelled"):
        return {"taskId": req.taskId, "cancelled": False, "reason": f"任务已 {task.status}"}
    task.status = "cancelled"
    task.finished_at = datetime.utcnow()
    await db.commit()
    return {"taskId": req.taskId, "cancelled": True}


# ============================================================
# 6.6 模型管理
# ============================================================

async def model_list(db: AsyncSession) -> dict:
    """模型列表：5 个核心 AI 模型 + 各自配置/用量/状态"""
    # 并行查所有需要异步查的项
    llm_cfg_task = _get_llm_config(db)
    llm_ver_task = _get_llm_version(db)
    # 查每个模型的月用量
    usage_rows = (await db.execute(
        select(AITask.model, func.count(AITask.id))
        .where(AITask.model.isnot(None))
        .group_by(AITask.model)
    )).all()
    usage = {m: c for m, c in usage_rows}
    llm_config_dict, llm_version = await asyncio.gather(llm_cfg_task, llm_ver_task)

    # 读各模型 Redis 配置（如果有用户改过）
    def _cfg_or_env(model_id: str, env_default: dict) -> dict:
        """从 Redis 读 user override，没有就返回 env default"""
        return env_default  # 简化：先都返回 env default；下方按需补

    # 5 个模型：内置 3 个 + 外部 2 个
    models = [
        {
            "id": "paddleocr-v3",
            "name": "PaddleOCR 发票识别",
            "type": "ocr",
            "category": "内置自研",
            "description": "自建 PaddleOCR 微服务，识别发票字段（金额/税率/销方）。延迟低、无外部费用。",
            "status": "healthy",
            "version": "1.2.0",
            "metrics": {"latencyMs": 400, "accuracy": 0.962, "qps": 5},
            "config": await _get_ocr_config(db),
            "configurable": ["confidenceThreshold", "enableLineItems", "maxFileSizeMB"],
            "costPerCallCents": 0,
            "monthlyUsage": usage.get("paddleocr-v3", 0),
        },
        {
            "id": "llm",
            "name": "通用大模型 (LLM)",
            "type": "llm",
            "category": "外部 SaaS / 自建",
            "description": "AI 起草/抽取/问答的底层 LLM。支持 12 家国内外大模型服务商（OpenAI/通义千问/DeepSeek/MiniMax/智谱/百度/腾讯/Moonshot/豆包/Stepfun/Ollama/自定义）。",
            "status": "healthy",
            "version": llm_version,
            "metrics": {"latencyMs": 1200, "tokensPerSec": 80, "qps": 10},
            "config": llm_config_dict,
            "configurable": ["provider", "baseUrl", "apiKey", "model", "contextLimit", "temperature", "maxTokens", "streaming"],
            "providers": [
                {"value": "openai", "label": "OpenAI 兼容（含 GPT-4o/o1/o3）", "defaultUrl": "https://api.openai.com/v1", "defaultModel": "gpt-4o"},
                {"value": "qwen", "label": "阿里通义 Qwen", "defaultUrl": "https://dashscope.aliyuncs.com/compatible-mode/v1", "defaultModel": "qwen-max"},
                {"value": "deepseek", "label": "DeepSeek", "defaultUrl": "https://api.deepseek.com/v1", "defaultModel": "deepseek-chat"},
                {"value": "minimax", "label": "MiniMax", "defaultUrl": "https://api.minimaxi.com/v1", "defaultModel": "MiniMax-Text-01"},
                {"value": "zhipu", "label": "智谱 GLM", "defaultUrl": "https://open.bigmodel.cn/api/paas/v4", "defaultModel": "glm-4-plus"},
                {"value": "baidu", "label": "百度 ERNIE", "defaultUrl": "https://qianfan.baidubce.com/v2", "defaultModel": "ernie-4.0-8k"},
                {"value": "tencent", "label": "腾讯混元", "defaultUrl": "https://hunyuan.cloud.tencent.com/v1", "defaultModel": "hunyuan-pro"},
                {"value": "moonshot", "label": "月之暗面 Moonshot", "defaultUrl": "https://api.moonshot.cn/v1", "defaultModel": "moonshot-v1-128k"},
                {"value": "doubao", "label": "字节豆包", "defaultUrl": "https://ark.cn-beijing.volces.com/api/v3", "defaultModel": "doubao-pro-128k"},
                {"value": "stepfun", "label": "阶跃星辰 Step", "defaultUrl": "https://api.stepfun.com/v1", "defaultModel": "step-1-128k"},
                {"value": "ollama", "label": "Ollama 本地（llama3.1 等）", "defaultUrl": "http://localhost:11434/v1", "defaultModel": "llama3.1"},
                {"value": "custom", "label": "自定义 OpenAI 兼容端点", "defaultUrl": "", "defaultModel": ""},
            ],
            "costPerCallCents": 2,
            "monthlyUsage": usage.get(llm_version, 0),
        },
        {
            "id": "risk-v2.3",
            "name": "RiskScan 风险扫描",
            "type": "risk",
            "category": "内置自研",
            "description": "合同/项目/凭证异常实时标红。基于规则 + 行业历史风险库。",
            "status": "healthy",
            "version": "2.3.1",
            "metrics": {"latencyMs": 300, "accuracy": 0.85, "qps": 20},
            "config": await _get_risk_config(db),
            "configurable": ["thresholds.high", "thresholds.medium", "thresholds.low", "enableAutoScan"],
            "costPerCallCents": 1,
            "monthlyUsage": usage.get("risk-v2.3", 0),
        },
        {
            "id": "guoshui-verify",
            "name": "国税查验接口",
            "type": "verify",
            "category": "外部 SaaS",
            "description": "对接国税总局发票查验平台，验证发票真伪。仅需 AppCode，无需 API Key。",
            "status": "healthy",
            "version": "v3",
            "metrics": {"latencyMs": 1500, "successRate": 0.98, "qps": 3},
            "config": await _get_verify_config(db),
            "configurable": ["appCode", "useSandbox", "timeoutSec"],
            "costPerCallCents": 5,
            "monthlyUsage": usage.get("guoshui-verify", 0),
        },
        {
            "id": "nuonuo-fallback",
            "name": "诺诺发票兜底",
            "type": "ocr_fallback",
            "category": "外部 SaaS",
            "description": "PaddleOCR 失败时的兜底识别服务（诺诺电子发票 API）。按调用计费。",
            "status": "down",
            "version": "v2",
            "metrics": {"latencyMs": 2200, "accuracy": 0.93, "qps": 2},
            "config": await _get_nuonuo_config(db),
            "configurable": ["appKey", "appSecret", "enabled", "fallbackThreshold"],
            "costPerCallCents": 8,
            "monthlyUsage": usage.get("nuonuo-fallback", 0),
        },
    ]
    return {"models": models}


async def model_config(db: AsyncSession, req) -> dict:
    """更新模型配置（持久化到 Redis，按 modelId 区分）"""
    cfg = dict(req.config or {})
    # 敏感字段脱敏后再返回
    masked_cfg = dict(cfg)
    for secret_key in ("apiKey", "appCode", "appKey", "appSecret"):
        v = masked_cfg.get(secret_key, "")
        if isinstance(v, str) and len(v) > 8:
            masked_cfg[f"_{secret_key}Masked"] = v[:4] + "***" + v[-4:]
            masked_cfg[secret_key] = "***"  # 不回显
    # 存 Redis：key = ai:model:{modelId}
    key = f"ai:model:{req.modelId}"
    await cache_mod.set_(key, {
        "config": cfg,  # Redis 里存明文（用于真调用）
        "enabled": req.enabled,
        "updatedAt": datetime.utcnow().isoformat(),
    }, ttl=86400 * 30)
    return {
        "modelId": req.modelId,
        "config": masked_cfg,
        "enabled": req.enabled,
        "updated": True,
    }


async def _get_ocr_config(db: AsyncSession) -> dict:
    cached = await cache_mod.get("ai:model:paddleocr-v3")
    if cached and isinstance(cached, dict):
        return cached.get("config") or {}
    return {
        "confidenceThreshold": 0.7,
        "enableLineItems": True,
        "maxFileSizeMB": 20,
        "endpoint": settings.AI_OCR_ENDPOINT if hasattr(settings, "AI_OCR_ENDPOINT") else "http://localhost:8001",
    }


async def _get_risk_config(db: AsyncSession) -> dict:
    cached = await cache_mod.get("ai:model:risk-v2.3")
    if cached and isinstance(cached, dict):
        return cached.get("config") or {}
    return {
        "thresholds": {"high": 60, "medium": 75, "low": 90},
        "enableAutoScan": True,
    }


async def _get_verify_config(db: AsyncSession) -> dict:
    cached = await cache_mod.get("ai:model:guoshui-verify")
    if cached and isinstance(cached, dict):
        return cached.get("config") or {}
    return {
        "appCode": "",
        "useSandbox": True,
        "timeoutSec": 10,
        "apiUrl": "http://127.0.0.1:8002/open/v1/services",
    }


async def _get_nuonuo_config(db: AsyncSession) -> dict:
    cached = await cache_mod.get("ai:model:nuonuo-fallback")
    if cached and isinstance(cached, dict):
        return cached.get("config") or {}
    return {
        "appKey": "",
        "appSecret": "",
        "enabled": False,
        "fallbackThreshold": 0.5,
    }


async def _get_llm_config(db: AsyncSession) -> dict:
    """从 Redis 读 LLM 配置；没有则 fallback 到 settings.AI_LLM_* 环境变量"""
    cached = await cache_mod.get("ai:model:llm")
    if cached and isinstance(cached, dict):
        cfg = cached.get("config") or {}
        # 不返回完整 apiKey（前端列表也不该看到）
        masked = dict(cfg)
        if masked.get("apiKey"):
            k = str(masked["apiKey"])
            masked["apiKey"] = k[:4] + "***" + k[-4:] if len(k) > 8 else "***"
        masked.setdefault("temperature", 0.7)
        masked.setdefault("maxTokens", 2048)
        masked.setdefault("systemPrompt", "你是数智化系统 AI 助手")
        return masked
    return {
        "provider": "qwen",
        "baseUrl": settings.AI_LLM_ENDPOINT if hasattr(settings, "AI_LLM_ENDPOINT") else "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "apiKey": (settings.AI_LLM_API_KEY[:4] + "***" + settings.AI_LLM_API_KEY[-4:]) if (hasattr(settings, "AI_LLM_API_KEY") and len(settings.AI_LLM_API_KEY) > 8) else "",
        "model": settings.AI_LLM_MODEL if hasattr(settings, "AI_LLM_MODEL") else "qwen2.5-7b-instruct",
        "contextLimit": 131072,
        "temperature": 0.7,
        "maxTokens": 2048,
        "systemPrompt": "你是数智化系统 AI 助手",
    }


async def _get_llm_version(db: AsyncSession) -> str:
    cached = await cache_mod.get("ai:model:llm")
    if cached and isinstance(cached, dict):
        model = (cached.get("config") or {}).get("model")
        if model:
            return str(model)
    return settings.AI_LLM_MODEL if hasattr(settings, "AI_LLM_MODEL") else "qwen2.5-7b-instruct"


async def get_active_llm_config(db: AsyncSession) -> dict:
    """给 ai_client.py 用：返回完整配置（含明文 API Key），无 fallback"""
    cached = await cache_mod.get("ai:model:llm")
    if cached and isinstance(cached, dict):
        cfg = cached.get("config") or {}
        if cfg.get("baseUrl") and cfg.get("model"):
            return cfg
    # fallback: 用环境变量
    return {
        "provider": "qwen",
        "baseUrl": settings.AI_LLM_ENDPOINT if hasattr(settings, "AI_LLM_ENDPOINT") else "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "apiKey": settings.AI_LLM_API_KEY if hasattr(settings, "AI_LLM_API_KEY") else "",
        "model": settings.AI_LLM_MODEL if hasattr(settings, "AI_LLM_MODEL") else "qwen2.5-7b-instruct",
        "contextLimit": 131072,
        "temperature": 0.7,
        "maxTokens": 2048,
    }


async def model_test_connection(base_url: str, api_key: str, model: str) -> dict:
    """测试 LLM 连通性：发一个最小 /chat/completions 请求"""
    import httpx
    import time
    if not base_url:
        return {"ok": False, "message": "Base URL 不能为空"}
    base_url = base_url.rstrip("/")
    url = f"{base_url}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model or "gpt-4o-mini",
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 8,
        "temperature": 0,
    }
    t0 = time.time()
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(url, json=payload, headers=headers)
        latency = int((time.time() - t0) * 1000)
        if r.status_code == 200:
            return {"ok": True, "message": f"连接成功（HTTP 200）", "latencyMs": latency}
        # 401/403 通常意味着 key 错；其他是服务/网络问题
        try:
            err = r.json()
            err_msg = err.get("error", {}).get("message") or err.get("message") or str(err)[:200]
        except Exception:
            err_msg = r.text[:200]
        return {
            "ok": False,
            "message": f"HTTP {r.status_code}：{err_msg}",
            "latencyMs": latency,
        }
    except httpx.TimeoutException:
        return {"ok": False, "message": f"连接超时（10s）", "latencyMs": int((time.time() - t0) * 1000)}
    except Exception as e:
        return {"ok": False, "message": f"请求失败：{type(e).__name__}: {str(e)[:200]}"}



# ============================================================
# 6.7 反馈中心
# ============================================================

async def feedback_submit(db: AsyncSession, req, user_id: int) -> dict:
    fb = AIFeedback(
        tenant_id=1, target_type=req.targetType, target_id=req.targetId,
        user_id=user_id, rating=req.rating, category=req.category,
        comment=req.comment, tags=req.tags,
    )
    db.add(fb)
    await db.commit()
    return {"feedbackId": fb.id, "saved": True}


# ============================================================
# 全局 SSE 入口（/api/v1/ai/stream）
# ============================================================

async def stream_event(channel: str):
    """通用 SSE 事件流（复用 core/sse.py）"""
    from app.core.sse import event_stream
    return event_stream(f"ai:{channel}")
