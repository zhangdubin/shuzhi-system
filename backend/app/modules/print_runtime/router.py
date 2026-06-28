"""UDPE HTTP 路由。

设计文档：plans/udpe-design/design.md §五 5.1-5.2

M1 阶段 2：8 个端点 + service 占位。
M1 阶段 3：render/preview 接 PdfRenderer / HtmlRenderer。
"""
import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.print import BindContext, PrintRequest as PR
from app.core.security import (
    CurrentUser, get_current_user, require_permission,
)
from app.modules.print_runtime import schemas, service

logger = logging.getLogger(__name__)

# ===== 模板管理（admin）=====
admin_router = APIRouter()


@admin_router.get("/print-templates", summary="打印模板列表")
async def list_templates(
    docType: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("print:template:read")),
):
    rows, total = await service.list_templates(db, docType, status, page, pageSize)
    return {
        "code": 0,
        "data": {
            "list": [t.to_dict() for t in rows],
            "total": total,
        },
    }


@admin_router.get("/print-templates/{tid}", summary="打印模板详情")
async def get_template(
    tid: int,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("print:template:read")),
):
    from app.core.print import PrintTemplateNotFoundError
    from sqlalchemy import select
    from app.modules.print_runtime.models import PrintTemplate
    t = (await db.execute(select(PrintTemplate).where(PrintTemplate.id == tid))).scalar_one_or_none()
    if not t:
        raise PrintTemplateNotFoundError(f"模板不存在：{tid}")
    return {"code": 0, "data": t.to_dict()}


@admin_router.post("/print-templates", summary="新建打印模板")
async def create_template(
    payload: schemas.PrintTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("print:template:write")),
):
    t = await service.create_template(
        db,
        code=payload.code,
        name=payload.name,
        doc_type=payload.docType,
        paper=payload.paper,
        width_mm=payload.widthMm,
        height_mm=payload.heightMm,
        orientation=payload.orientation,
        description=payload.description,
        schema_json=payload.schemaJson,
        is_default=payload.isDefault,
        created_by=current_user.id,
    )
    return {"code": 0, "data": t.to_dict(), "message": "已创建（draft 状态）"}


@admin_router.post("/print-templates/update", summary="更新打印模板")
async def update_template(
    payload: schemas.PrintTemplateUpdate,
    tid: int = Query(..., description="模板 ID"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("print:template:write")),
):
    t = await service.update_template(
        db, tid,
        name=payload.name, paper=payload.paper, width_mm=payload.widthMm,
        height_mm=payload.heightMm, orientation=payload.orientation,
        description=payload.description, schema_json=payload.schemaJson,
        is_default=payload.isDefault, version_note=payload.versionNote,
        operator_id=current_user.id,
    )
    return {"code": 0, "data": t.to_dict(), "message": "已更新"}


@admin_router.post("/print-templates/publish", summary="发布模板（draft→active）")
async def publish_template(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("print:template:admin")),
):
    tid = int(payload.get("id") or 0)
    if not tid:
        from app.core.exceptions import ParamErrorException
        raise ParamErrorException("缺少 id")
    t = await service.publish_template(db, tid)
    return {"code": 0, "data": t.to_dict(), "message": "已发布"}


@admin_router.post("/print-templates/archive", summary="归档模板（→archived）")
async def archive_template(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("print:template:admin")),
):
    tid = int(payload.get("id") or 0)
    if not tid:
        from app.core.exceptions import ParamErrorException
        raise ParamErrorException("缺少 id")
    t = await service.archive_template(db, tid)
    return {"code": 0, "data": t.to_dict(), "message": "已归档"}


@admin_router.post("/print-templates/delete", summary="删除打印模板")
async def delete_template(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("print:template:admin")),
):
    tid = int(payload.get("id") or 0)
    if not tid:
        from app.core.exceptions import ParamErrorException
        raise ParamErrorException("缺少 id")
    await service.delete_template(db, tid)
    return {"code": 0, "message": "已删除"}


# ===== M4 阶段 4: 模板版本历史 =====

@admin_router.get("/print-templates/{tid}/versions", summary="模板版本历史")
async def list_versions(
    tid: int,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("print:template:read")),
):
    from sqlalchemy import select
    from app.modules.print_runtime.models import PrintTemplateVersion
    rows = (await db.execute(
        select(PrintTemplateVersion)
        .where(PrintTemplateVersion.template_id == tid)
        .order_by(PrintTemplateVersion.version.desc())
    )).scalars().all()
    return {
        "code": 0,
        "data": [
            {
                "id": v.id,
                "version": v.version,
                "note": v.note,
                "snapshotBy": v.snapshot_by,
                "snapshotAt": str(v.snapshot_at) if v.snapshot_at else None,
            }
            for v in rows
        ],
    }


@admin_router.get("/print-templates/{tid}/versions/{ver}", summary="模板版本详情（含 schemaJson）")
async def get_version(
    tid: int,
    ver: int,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("print:template:read")),
):
    from sqlalchemy import select
    from app.modules.print_runtime.models import PrintTemplateVersion
    v = (await db.execute(
        select(PrintTemplateVersion)
        .where(PrintTemplateVersion.template_id == tid, PrintTemplateVersion.version == ver)
    )).scalar_one_or_none()
    if not v:
        from app.core.exceptions import ParamErrorException
        raise ParamErrorException(f"版本不存在: template={tid}, version={ver}")
    return {
        "code": 0,
        "data": {
            "id": v.id,
            "templateId": v.template_id,
            "version": v.version,
            "schemaJson": v.schema_json,
            "note": v.note,
            "snapshotBy": v.snapshot_by,
            "snapshotAt": str(v.snapshot_at) if v.snapshot_at else None,
        },
    }


@admin_router.post("/print-templates/{tid}/restore", summary="回滚模板到指定版本")
async def restore_version(
    tid: int,
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("print:template:write")),
):
    ver = payload.get("version")
    if not ver:
        from app.core.exceptions import ParamErrorException
        raise ParamErrorException("缺少 version")
    from sqlalchemy import select
    from app.modules.print_runtime.models import PrintTemplate, PrintTemplateVersion
    t = (await db.execute(select(PrintTemplate).where(PrintTemplate.id == tid))).scalar_one_or_none()
    if not t:
        from app.core.print import PrintTemplateNotFoundError
        raise PrintTemplateNotFoundError(f"模板不存在: {tid}")
    v = (await db.execute(
        select(PrintTemplateVersion)
        .where(PrintTemplateVersion.template_id == tid, PrintTemplateVersion.version == ver)
    )).scalar_one_or_none()
    if not v:
        from app.core.exceptions import ParamErrorException
        raise ParamErrorException(f"版本不存在: {ver}")
    # 保存当前状态为新版本（作为回滚前快照）
    snapshot = PrintTemplateVersion(
        template_id=t.id, version=t.version, schema_json=t.schema_json,
        snapshot_by=current_user.id, note=f"回滚前快照 (v{t.version})",
    )
    db.add(snapshot)
    # 回滚
    t.schema_json = v.schema_json
    t.version += 1
    await db.commit()
    await db.refresh(t)
    from app.modules.print_runtime.service import invalidate_template_cache
    await invalidate_template_cache(t.code)
    return {"code": 0, "data": t.to_dict(), "message": f"已回滚到 v{ver}"}


# ===== M5 阶段 2: 缓存预热 =====

@admin_router.post("/print-templates/cache/warmup", summary="预热模板缓存（加载所有 active 模板到 Redis）")
async def warmup_cache(
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("print:template:admin")),
):
    from sqlalchemy import select
    from app.modules.print_runtime.models import PrintTemplate
    from app.modules.print_runtime.service import _template_cache_key, _template_to_cache_dict, invalidate_template_cache
    from app.core.cache import set_ as cache_set

    rows = (await db.execute(
        select(PrintTemplate).where(PrintTemplate.status == "active")
    )).scalars().all()
    warmed = 0
    for t in rows:
        key = _template_cache_key(t.code)
        await cache_set(key, _template_to_cache_dict(t), ttl=3600)
        warmed += 1
    return {"code": 0, "message": f"已预热 {warmed} 个模板缓存", "data": {"count": warmed}}


# ===== M5 阶段 3: 打印用量统计 =====

@admin_router.get("/print-stats", summary="打印用量统计（仪表盘用）")
async def print_stats(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("print:document:read")),
):
    from sqlalchemy import func, select, text
    from app.modules.print_runtime.models import PrintLog
    from datetime import datetime, timedelta

    since = datetime.now() - timedelta(days=days)

    # 总量 / 成功 / 失败
    total = (await db.execute(
        select(func.count()).select_from(PrintLog).where(PrintLog.created_at >= since)
    )).scalar() or 0
    success = (await db.execute(
        select(func.count()).select_from(PrintLog).where(PrintLog.created_at >= since, PrintLog.status == "success")
    )).scalar() or 0
    failed = total - success

    # 平均耗时
    avg_ms = (await db.execute(
        select(func.avg(PrintLog.elapsed_ms)).where(PrintLog.created_at >= since, PrintLog.elapsed_ms.isnot(None))
    )).scalar() or 0

    # PDF 总大小
    total_pdf_size = (await db.execute(
        select(func.sum(PrintLog.pdf_size)).where(PrintLog.created_at >= since, PrintLog.pdf_size.isnot(None))
    )).scalar() or 0

    # 按模板统计 top 5
    top_templates = (await db.execute(
        select(PrintLog.template_code, func.count().label("cnt"))
        .where(PrintLog.created_at >= since)
        .group_by(PrintLog.template_code)
        .order_by(text("cnt DESC"))
        .limit(5)
    )).all()

    # 按天统计 (最近 7 天)
    daily = []
    for i in range(6, -1, -1):
        day = datetime.now().date() - timedelta(days=i)
        day_start = datetime.combine(day, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        cnt = (await db.execute(
            select(func.count()).select_from(PrintLog).where(
                PrintLog.created_at >= day_start, PrintLog.created_at < day_end
            )
        )).scalar() or 0
        daily.append({"date": day.isoformat(), "count": cnt})

    return {
        "code": 0,
        "data": {
            "total": total,
            "success": success,
            "failed": failed,
            "avgElapsedMs": round(float(avg_ms), 1),
            "totalPdfSizeMb": round(total_pdf_size / 1024 / 1024, 2) if total_pdf_size else 0,
            "topTemplates": [{"code": r[0], "count": r[1]} for r in top_templates],
            "daily": daily,
        },
    }


# ===== 运行时 =====
runtime_router = APIRouter()


def _build_bind_ctx(current_user, options: Optional[schemas.PrintOptions]) -> BindContext:
    return BindContext(
        operator_id=current_user.id,
        operator_name=current_user.name,
        source_module=options.sourceModule if options else None,
        source_id=options.sourceId if options else None,
        locale=options.locale if options and options.locale else "zh",
    )


def _build_print_request(req: schemas.PrintRequest, render_mode: str) -> PR:
    """router → service 的 PrintRequest 转换。"""
    options_dict = req.options.model_dump() if req.options else {}
    options_dict["renderMode"] = render_mode  # 强制 override
    full_req = PR(
        template_code=req.templateCode,
        data=req.data or {},
        options=options_dict,
    )
    return full_req


@runtime_router.post("/print/preview-schema", summary="编辑器实时预览 (M3 阶段 1, 不写日志)")
async def preview_by_schema(
    req: schemas.PrintPreviewBySchemaRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("print:template:write")),
):
    """M3 阶段 1: 编辑器实时预览, 直接传 schemaJson 渲染 (无需保存模板).
    不写 print_logs (预览不应影响实际日志).
    """
    bind_ctx = BindContext(
        operator_id=_user.id,
        operator_name=_user.name,
        source_module=(req.options.sourceModule if req.options else "editor"),
        source_id=(req.options.sourceId if req.options else None),
    )
    options_dict = req.options.model_dump() if req.options else {}
    options_dict["renderMode"] = "html"
    result = await service.render_by_schema(
        db, req.docType, req.schemaJson, req.data or {}, options_dict, bind_ctx
    )
    return {
        "code": 0,
        "data": {
            "html": result.content.decode("utf-8") if isinstance(result.content, (bytes, bytearray)) else str(result.content),
            "elapsedMs": result.elapsed_ms,
        },
    }


@runtime_router.post("/print/preview", summary="预览（返回 HTML 字符串）")
async def preview(
    req: schemas.PrintRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("print:document:read")),
):
    bind_ctx = _build_bind_ctx(current_user, req.options)
    full_req = _build_print_request(req, render_mode="html")
    result = await service.render(db, full_req, bind_ctx)
    # 解析日志 id
    log_id = result.log_id
    # 反查 template code
    template = await service.get_template_by_code(db, req.templateCode)
    return {
        "code": 0,
        "data": {
            "html": result.content.decode("utf-8") if isinstance(result.content, (bytes, bytearray)) else str(result.content),
            "templateId": result.template_id,
            "logId": log_id,
            "templateCode": template.code,
            "templateName": template.name,
            "elapsedMs": result.elapsed_ms,
        },
    }


@runtime_router.post("/print/pdf", summary="导出 PDF")
async def export_pdf(
    req: schemas.PrintRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("print:document:export")),
):
    bind_ctx = _build_bind_ctx(current_user, req.options)
    full_req = _build_print_request(req, render_mode="pdf")
    result = await service.render(db, full_req, bind_ctx)
    return Response(
        content=result.content,
        media_type=result.mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{result.filename}"; filename*=UTF-8\'\'{result.filename}',
            "X-Print-Log-Id": str(result.log_id),
        },
    )


@runtime_router.post("/print/log", summary="日志查询")
async def list_logs(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("print:document:read")),
):
    rows, total = await service.list_logs(
        db,
        page=int(payload.get("page") or 1),
        page_size=int(payload.get("pageSize") or 50),
        template_code=payload.get("templateCode"),
        operator_id=payload.get("operatorId"),
    )
    return {
        "code": 0,
        "data": {
            "list": [r.to_dict() for r in rows],
            "total": total,
        },
    }


@runtime_router.post("/print/batch", summary="批量打印（合并 PDF, M2 阶段 9）")
async def batch_pdf(
    req: schemas.PrintBatchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("print:document:export")),
):
    """批量渲染并合并为单个 PDF 文件.

    入参:
      - templateCode: 同一模板 (业务类型隐含在模板 docType 中)
      - items: 业务主键列表, 1-100 条
      - options: 与单条 print/pdf 一致

    出参:
      - application/pdf 流 (Content-Disposition 触发下载)
      - X-Print-Batch-* 头返回统计信息
    """
    bind_ctx = _build_bind_ctx(current_user, req.options)
    bind_ctx.source_module = (req.options.sourceModule if req.options else None) or "batch"
    item_ids = [it.id for it in req.items]

    merged_bytes, log_ids, failed_items, elapsed = await service.render_batch(
        db, req.templateCode, item_ids, bind_ctx
    )

    # 拿到 template name 给 filename 用
    template = await service.get_template_by_code(db, req.templateCode)
    fname = f"batch_{template.code}_{int(time.time())}.pdf"

    headers = {
        "Content-Disposition": f"attachment; filename=\"{fname}\"; filename*=UTF-8''" + fname,
        "X-Print-Batch-Total": str(len(item_ids)),
        "X-Print-Batch-Success": str(len(log_ids)),
        "X-Print-Batch-Failed": str(len(failed_items)),
        "X-Print-Batch-Elapsed-Ms": str(elapsed),
    }
    return Response(
        content=merged_bytes,
        media_type="application/pdf",
        headers=headers,
    )


# ===== M4 阶段 1: 异步批量打印 + SSE 进度 =====

import asyncio
import uuid as _uuid

# 内存任务表 (V1 简化; 生产环境可换 Redis Hash)
_batch_jobs: dict = {}


@runtime_router.post("/print/batch/async", summary="异步批量打印（后台执行 + SSE 进度）")
async def batch_pdf_async(
    req: schemas.PrintBatchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("print:document:export")),
):
    """启动异步批量打印任务.

    返回 job_id, 前端通过 SSE /sse/batch/{job_id} 监听进度.
    任务完成后通过 GET /print/batch/async/{job_id}/download 下载 PDF.
    """
    job_id = str(_uuid.uuid4())[:12]
    item_ids = [it.id for it in req.items]
    bind_ctx = _build_bind_ctx(current_user, req.options)
    bind_ctx.source_module = (req.options.sourceModule if req.options else None) or "batch"

    _batch_jobs[job_id] = {
        "status": "pending",
        "total": len(item_ids),
        "done": 0,
        "failed": 0,
        "errors": [],
        "pdf_bytes": None,
        "elapsed_ms": 0,
        "user_id": current_user.id,
    }

    # 启动后台任务
    asyncio.create_task(_run_batch_job(job_id, req.templateCode, item_ids, bind_ctx))

    return {"code": 0, "data": {"jobId": job_id, "total": len(item_ids)}}


async def _run_batch_job(job_id: str, template_code: str, item_ids: list, bind_ctx):
    """后台执行批量打印, 逐条发布 SSE 进度."""
    from app.core.sse import publish_event
    from app.core.database import AsyncSessionLocal

    job = _batch_jobs[job_id]
    job["status"] = "running"
    channel = f"sse:batch:{job_id}"  # SSE endpoint prepends "sse:" to path
    started = time.time()

    await publish_event(channel, "batch_start", {
        "jobId": job_id, "total": len(item_ids),
    })

    pdf_chunks = []
    log_ids = []

    async with AsyncSessionLocal() as db:
        bind_ctx.extra["db"] = db
        for i, item_id in enumerate(item_ids):
            try:
                req_obj = PR(
                    template_code=template_code,
                    data={"_resolver": item_id},
                    options={
                        "renderMode": "pdf",
                        "sourceModule": bind_ctx.source_module or "batch",
                        "sourceId": str(item_id),
                    },
                )
                result = await service.render(db, req_obj, bind_ctx)
                pdf_chunks.append(result.content)
                log_ids.append(result.log_id)
                job["done"] += 1
            except Exception as e:
                job["failed"] += 1
                job["errors"].append({"id": str(item_id), "error": str(e)[:200]})

            await publish_event(channel, "batch_progress", {
                "jobId": job_id,
                "current": i + 1,
                "total": len(item_ids),
                "done": job["done"],
                "failed": job["failed"],
            })

    # 合并 PDF
    if pdf_chunks:
        merged = _merge_pdfs_fn(pdf_chunks)
        job["pdf_bytes"] = merged
        job["status"] = "done"
    else:
        job["status"] = "failed"

    elapsed = int((time.time() - started) * 1000)
    job["elapsed_ms"] = elapsed

    await publish_event(channel, "batch_done", {
        "jobId": job_id,
        "status": job["status"],
        "done": job["done"],
        "failed": job["failed"],
        "elapsedMs": elapsed,
    })


def _merge_pdfs_fn(pdf_chunks: list) -> bytes:
    """合并多个 PDF bytes (复用 pymupdf)."""
    import fitz
    merged_doc = fitz.open()
    try:
        for chunk in pdf_chunks:
            src = fitz.open("pdf", chunk)
            merged_doc.insert_pdf(src)
            src.close()
        return merged_doc.tobytes()
    finally:
        merged_doc.close()


@runtime_router.get("/print/batch/async/{job_id}/status", summary="查询异步批量打印任务状态")
async def batch_job_status(
    job_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    job = _batch_jobs.get(job_id)
    if not job:
        from app.core.exceptions import ParamErrorException
        raise ParamErrorException(f"任务不存在: {job_id}")
    return {
        "code": 0,
        "data": {
            "jobId": job_id,
            "status": job["status"],
            "total": job["total"],
            "done": job["done"],
            "failed": job["failed"],
            "elapsedMs": job["elapsed_ms"],
            "errors": job["errors"],
        },
    }


@runtime_router.get("/print/batch/async/{job_id}/download", summary="下载异步批量打印结果")
async def batch_job_download(
    job_id: str,
    current_user: CurrentUser = Depends(get_current_user),
):
    job = _batch_jobs.get(job_id)
    if not job:
        from app.core.exceptions import ParamErrorException
        raise ParamErrorException(f"任务不存在: {job_id}")
    if job["status"] != "done" or not job["pdf_bytes"]:
        from app.core.exceptions import ParamErrorException
        raise ParamErrorException("任务尚未完成")
    fname = f"batch_{job_id}.pdf"
    headers = {
        "Content-Disposition": f"attachment; filename=\"{fname}\"",
    }
    return Response(
        content=job["pdf_bytes"],
        media_type="application/pdf",
        headers=headers,
    )


# ===== M3 阶段 4: Excel 模板导入 =====

@admin_router.post("/print-templates/import/excel/preview", summary="Excel 模板导入预览 (M3 阶段 4)")
async def preview_excel_import(
    file: UploadFile = File(..., description="xlsx 文件"),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("print:template:write")),
):
    """上传 xlsx → 解析为 grid schemaJson + 预览 HTML."""
    from app.modules.print_runtime.importers.excel_importer import parse_excel
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise ParamErrorException("仅支持 .xlsx 文件")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise ParamErrorException("文件过大 (上限 10MB)")
    try:
        result = parse_excel(content)
    except Exception as e:
        logger.exception("[UDPE] Excel 解析失败")
        raise ParamErrorException(f"Excel 解析失败: {e}")
    # 渲染每个 sheet 的预览
    from app.core.print import RendererRegistry, RenderContext
    previews = []
    for s in result["sheets"]:
        try:
            renderer = RendererRegistry.get("html")
            ctx = RenderContext(
                render_mode="html", copies=1, watermark=None,
                filename="preview.html", options={"renderMode": "html"},
                bind_ctx=BindContext(operator_id=_user.id, operator_name=_user.name, source_module="excel_import"),
            )
            tpl = {"code": "import_preview", "docType": "general", "version": 0, **s["schemaJson"]}
            html_bytes = await renderer.render(tpl, {}, ctx)
            html = html_bytes.decode("utf-8") if isinstance(html_bytes, (bytes, bytearray)) else str(html_bytes)
        except Exception as e:
            logger.warning(f"[UDPE] sheet {s['name']} 渲染失败: {e}")
            html = ""
        previews.append({**s, "html": html})
    return {"code": 0, "data": {
        "filename": file.filename,
        "totalSheets": result["totalSheets"],
        "sheets": previews,
    }}


@admin_router.post("/print-templates/import/excel/confirm", summary="Excel 导入确认保存 (M3 阶段 4)")
async def confirm_excel_import(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("print:template:write")),
):
    """把解析后的 schemaJson 保存为新模板."""
    from app.modules.print_runtime import service as template_service
    code = payload.get("code")
    name = payload.get("name")
    doc_type = payload.get("docType")
    if not code or not name or not doc_type:
        raise ParamErrorException("缺少必填字段: code / name / docType")
    schema_json = payload.get("schemaJson")
    if not schema_json:
        raise ParamErrorException("缺少 schemaJson")
    t = await template_service.create_template(
        db,
        code=code,
        name=name,
        doc_type=doc_type,
        paper=payload.get("paper", "A4"),
        width_mm=payload.get("widthMm"),
        height_mm=payload.get("heightMm"),
        orientation=payload.get("orientation", "portrait"),
        description=payload.get("description", f"Excel 导入自 {payload.get('sourceFile', '?')} / {payload.get('sourceSheet', '?')}"),
        schema_json=schema_json,
        is_default=False,
        created_by=current_user.id,
    )
    return {"code": 0, "data": t.to_dict(), "message": "已创建 (draft 状态)"}


# ===== M3 阶段 4 下半: Word 模板导入 =====

@admin_router.post("/print-templates/import/docx/preview", summary="Word 模板导入预览 (M3 阶段 4 下半)")
async def preview_docx_import(
    file: UploadFile = File(..., description="docx 文件"),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("print:template:write")),
):
    """上传 docx → 解析为 grid schemaJson + 预览 HTML."""
    from app.modules.print_runtime.importers.docx_importer import parse_docx
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise ParamErrorException("仅支持 .docx 文件")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise ParamErrorException("文件过大 (上限 10MB)")
    try:
        result = parse_docx(content)
    except Exception as e:
        logger.exception("[UDPE] Word 解析失败")
        raise ParamErrorException(f"Word 解析失败: {e}")
    # 渲染预览
    from app.core.print import RendererRegistry, RenderContext
    try:
        renderer = RendererRegistry.get("html")
        ctx = RenderContext(
            render_mode="html", copies=1, watermark=None,
            filename="preview.html", options={"renderMode": "html"},
            bind_ctx=BindContext(operator_id=_user.id, operator_name=_user.name, source_module="docx_import"),
        )
        tpl = {"code": "import_preview", "docType": "general", "version": 0, **result["schemaJson"]}
        html_bytes = await renderer.render(tpl, {}, ctx)
        html = html_bytes.decode("utf-8") if isinstance(html_bytes, (bytes, bytearray)) else str(html_bytes)
    except Exception as e:
        logger.warning(f"[UDPE] Word 渲染失败: {e}")
        html = ""
    return {"code": 0, "data": {
        "filename": file.filename,
        "totalElements": result["totalElements"],
        "schemaJson": result["schemaJson"],
        "placeholders": result["placeholders"],
        "warnings": result["warnings"],
        "html": html,
    }}


@admin_router.post("/print-templates/import/docx/confirm", summary="Word 导入确认保存 (M3 阶段 4 下半)")
async def confirm_docx_import(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("print:template:write")),
):
    """把解析后的 schemaJson 保存为新模板."""
    from app.modules.print_runtime import service as template_service
    code = payload.get("code")
    name = payload.get("name")
    doc_type = payload.get("docType")
    if not code or not name or not doc_type:
        raise ParamErrorException("缺少必填字段: code / name / docType")
    schema_json = payload.get("schemaJson")
    if not schema_json:
        raise ParamErrorException("缺少 schemaJson")
    t = await template_service.create_template(
        db,
        code=code,
        name=name,
        doc_type=doc_type,
        paper=payload.get("paper", "A4"),
        width_mm=payload.get("widthMm"),
        height_mm=payload.get("heightMm"),
        orientation=payload.get("orientation", "portrait"),
        description=payload.get("description", f"Word 导入自 {payload.get('sourceFile', '?')}"),
        schema_json=schema_json,
        is_default=False,
        created_by=current_user.id,
    )
    return {"code": 0, "data": t.to_dict(), "message": "已创建 (draft 状态)"}


# ===== M3 阶段 4: PDF 模板导入 =====

@admin_router.post("/print-templates/import/pdf/preview", summary="PDF 模板导入预览 (M3 阶段 4)")
async def preview_pdf_import(
    file: UploadFile = File(..., description="PDF 文件"),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("print:template:write")),
):
    """上传 PDF → 解析文本结构 + schemaJson + 预览 HTML."""
    from app.modules.print_runtime.importers.pdf_importer import preview_pdf_import as _preview
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise ParamErrorException("仅支持 .pdf 文件")
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise ParamErrorException("文件过大 (上限 20MB)")
    try:
        result = await _preview(content)
    except ValueError as e:
        raise ParamErrorException(str(e))
    except Exception as e:
        logger.exception("[UDPE] PDF 解析失败")
        raise ParamErrorException(f"PDF 解析失败: {e}")
    # 渲染预览 HTML
    from app.core.print import RendererRegistry, RenderContext
    html = ""
    try:
        renderer = RendererRegistry.get("html")
        ctx = RenderContext(
            render_mode="html", copies=1, watermark=None,
            filename="preview.html", options={"renderMode": "html"},
            bind_ctx=BindContext(operator_id=_user.id, operator_name=_user.name, source_module="pdf_import"),
        )
        tpl = {"code": "import_preview", "docType": "general", "version": 0, **result["schemaJson"]}
        html_bytes = await renderer.render(tpl, {}, ctx)
        html = html_bytes.decode("utf-8") if isinstance(html_bytes, (bytes, bytearray)) else str(html_bytes)
    except Exception as e:
        logger.warning(f"[UDPE] PDF 渲染预览失败: {e}")
    return {"code": 0, "data": {
        "filename": file.filename,
        "pages": result["pages"],
        "pageCount": result["pageCount"],
        "schemaJson": result["schemaJson"],
        "summary": result["summary"],
        "html": html,
    }}


@admin_router.post("/print-templates/import/pdf/confirm", summary="PDF 导入确认保存 (M3 阶段 4)")
async def confirm_pdf_import(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("print:template:write")),
):
    """把解析后的 schemaJson 保存为新模板."""
    from app.modules.print_runtime.importers.pdf_importer import confirm_pdf_import as _confirm
    from app.modules.print_runtime import service as template_service
    code = payload.get("code")
    name = payload.get("name")
    doc_type = payload.get("docType")
    if not code or not name or not doc_type:
        raise ParamErrorException("缺少必填字段: code / name / docType")
    schema_json = payload.get("schemaJson")
    if not schema_json:
        raise ParamErrorException("缺少 schemaJson")
    # 如果有 file_bytes (base64 编码), 带调整重新解析
    adjustments = payload.get("adjustments")
    if adjustments and payload.get("fileBytes"):
        import base64
        try:
            file_bytes = base64.b64decode(payload["fileBytes"])
            result = await _confirm(file_bytes, adjustments)
            schema_json = result["schemaJson"]
        except Exception as e:
            logger.warning(f"[UDPE] PDF 调整应用失败, 使用原 schemaJson: {e}")
    t = await template_service.create_template(
        db,
        code=code,
        name=name,
        doc_type=doc_type,
        paper=payload.get("paper", "A4"),
        width_mm=payload.get("widthMm"),
        height_mm=payload.get("heightMm"),
        orientation=payload.get("orientation", "portrait"),
        description=payload.get("description", f"PDF 导入自 {payload.get('sourceFile', '?')}"),
        schema_json=schema_json,
        is_default=False,
        created_by=current_user.id,
    )
    return {"code": 0, "data": t.to_dict(), "message": "已创建 (draft 状态)"}
