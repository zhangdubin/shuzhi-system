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


# ===== 运行时 =====
runtime_router = APIRouter()


def _build_bind_ctx(current_user, options: Optional[schemas.PrintOptions]) -> BindContext:
    return BindContext(
        operator_id=current_user.id,
        operator_name=current_user.name,
        source_module=options.sourceModule if options else None,
        source_id=options.sourceId if options else None,
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
