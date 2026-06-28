"""UDPE Service 编排（M1 阶段 3 完整版）。

设计文档：plans/udpe-design/design.md §六 6.1

M1 阶段 3 接入：
- D5  Redis 模板缓存（沿用 core.cache 风格；失效在写操作时）
- D6  Renderer + Resolver + VariableProvider 完整编排
        流程：load template → 启动各 Provider → 调 Resolver 取业务数据
            → 调 Renderer 渲染 → 写 print_logs
"""
import logging
import time
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import delete_pattern, get as cache_get, set_ as cache_set
from app.core.print import (
    BindContext,
    PrintDataResolveError,
    PrintRenderError,
    PrintRequest,
    PrintResult,
    PrintTemplateInactiveError,
    PrintTemplateNotFoundError,
    ProviderRegistry,
    RendererRegistry,
    RenderContext,
    ResolverRegistry,
)
from app.modules.print_runtime.models import PrintLog, PrintTemplate

logger = logging.getLogger(__name__)

# 模板缓存 TTL（5 分钟，模板更新后失效）
TEMPLATE_CACHE_TTL = 300


# ===== 模板加载（含缓存）=====

def _template_cache_key(code: str) -> str:
    return f"cache:print:template:{code}"


def _template_to_cache_dict(t: PrintTemplate) -> dict:
    """ORM → 缓存用 dict（renderer 需要的最小集）。"""
    return {
        "id": t.id,
        "code": t.code,
        "name": t.name,
        "doc_type": t.doc_type,
        "schema_json": t.schema_json or {},
        "version": t.version,
        "status": t.status,
    }


async def get_template_by_code(db: AsyncSession, code: str) -> PrintTemplate:
    """根据 code 查模板，未找到抛 PrintTemplateNotFoundError（不走缓存，方便管理后台即时看到状态）。"""
    t = (await db.execute(
        select(PrintTemplate).where(PrintTemplate.code == code)
    )).scalar_one_or_none()
    if not t:
        raise PrintTemplateNotFoundError(f"打印模板不存在：{code}")
    return t


async def get_active_template_by_code(
    db: AsyncSession, code: str, *, use_cache: bool = True,
) -> PrintTemplate:
    """渲染时用：优先走 Redis 缓存，draft/active 都能渲染。"""
    if use_cache:
        cached = await cache_get(_template_cache_key(code))
        if cached:
            # 缓存里只存了 dict，渲染流程要拿 schema_json 即可
            return cached  # type: ignore[return-value]

    t = await get_template_by_code(db, code)
    if t.status not in ("active", "draft"):
        raise PrintTemplateInactiveError(f"打印模板 {code} 状态为 {t.status}，不可用")
    cache_val = _template_to_cache_dict(t)
    await cache_set(_template_cache_key(code), cache_val, ttl=TEMPLATE_CACHE_TTL)
    return cache_val  # type: ignore[return-value]


async def invalidate_template_cache(code: str) -> int:
    """模板写操作后调用。"""
    return await delete_pattern(_template_cache_key(code))


# ===== 模板 CRUD =====

async def list_templates(
    db: AsyncSession,
    doc_type: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[PrintTemplate], int]:
    q = select(PrintTemplate)
    count_q = select(func.count()).select_from(PrintTemplate)
    if doc_type:
        q = q.where(PrintTemplate.doc_type == doc_type)
        count_q = count_q.where(PrintTemplate.doc_type == doc_type)
    if status:
        q = q.where(PrintTemplate.status == status)
        count_q = count_q.where(PrintTemplate.status == status)
    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(PrintTemplate.doc_type.asc(), PrintTemplate.id.asc())
    q = q.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return list(rows), total


async def create_template(
    db: AsyncSession,
    *,
    code: str,
    name: str,
    doc_type: str,
    paper: str = "A4",
    width_mm: float = 210,
    height_mm: float = 297,
    orientation: str = "portrait",
    description: Optional[str] = None,
    schema_json: Optional[dict] = None,
    is_default: bool = False,
    created_by: Optional[int] = None,
) -> PrintTemplate:
    if is_default:
        existing_defaults = (await db.execute(
            select(PrintTemplate).where(
                PrintTemplate.doc_type == doc_type,
                PrintTemplate.is_default == True,  # noqa: E712
            )
        )).scalars().all()
        for old in existing_defaults:
            old.is_default = False

    t = PrintTemplate(
        code=code, name=name, doc_type=doc_type,
        paper=paper, width_mm=width_mm, height_mm=height_mm, orientation=orientation,
        description=description,
        schema_json=schema_json or {},
        is_default=is_default, created_by=created_by, status="draft",
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    await invalidate_template_cache(code)
    return t


async def update_template(
    db: AsyncSession, template_id: int, *,
    name=None, paper=None, width_mm=None, height_mm=None,
    orientation=None, description=None, schema_json=None, is_default=None,
    version_note: Optional[str] = None,
    operator_id: Optional[int] = None,
) -> PrintTemplate:
    t = (await db.execute(
        select(PrintTemplate).where(PrintTemplate.id == template_id)
    )).scalar_one_or_none()
    if not t:
        raise PrintTemplateNotFoundError(f"模板不存在：{template_id}")

    if schema_json is not None and schema_json != t.schema_json:
        from app.modules.print_runtime.models import PrintTemplateVersion
        snapshot = PrintTemplateVersion(
            template_id=t.id, version=t.version, schema_json=t.schema_json,
            snapshot_by=operator_id, note=version_note,
        )
        db.add(snapshot)
        t.version += 1

    if name is not None: t.name = name
    if paper is not None: t.paper = paper
    if width_mm is not None: t.width_mm = width_mm
    if height_mm is not None: t.height_mm = height_mm
    if orientation is not None: t.orientation = orientation
    if description is not None: t.description = description
    if schema_json is not None: t.schema_json = schema_json
    if is_default is not None:
        t.is_default = is_default
        if is_default:
            others = (await db.execute(
                select(PrintTemplate).where(
                    PrintTemplate.doc_type == t.doc_type,
                    PrintTemplate.id != t.id,
                    PrintTemplate.is_default == True,  # noqa: E712
                )
            )).scalars().all()
            for o in others:
                o.is_default = False

    await db.commit()
    await db.refresh(t)
    await invalidate_template_cache(t.code)
    return t


async def publish_template(db: AsyncSession, template_id: int) -> PrintTemplate:
    t = (await db.execute(
        select(PrintTemplate).where(PrintTemplate.id == template_id)
    )).scalar_one_or_none()
    if not t:
        raise PrintTemplateNotFoundError(f"模板不存在：{template_id}")
    t.status = "active"
    await db.commit()
    await db.refresh(t)
    await invalidate_template_cache(t.code)
    return t


async def archive_template(db: AsyncSession, template_id: int) -> PrintTemplate:
    t = (await db.execute(
        select(PrintTemplate).where(PrintTemplate.id == template_id)
    )).scalar_one_or_none()
    if not t:
        raise PrintTemplateNotFoundError(f"模板不存在：{template_id}")
    t.status = "archived"
    await db.commit()
    await db.refresh(t)
    await invalidate_template_cache(t.code)
    return t


async def delete_template(db: AsyncSession, template_id: int) -> None:
    """删除模板（仅 draft/archived 状态允许）。"""
    t = (await db.execute(
        select(PrintTemplate).where(PrintTemplate.id == template_id)
    )).scalar_one_or_none()
    if not t:
        raise PrintTemplateNotFoundError(f"模板不存在：{template_id}")
    if t.status == "active":
        from app.core.exceptions import ParamErrorException
        raise ParamErrorException("已发布的模板不能删除，请先归档")
    await invalidate_template_cache(t.code)
    await db.delete(t)
    await db.commit()


# ===== 渲染编排（M1 阶段 3 完整版）=====

async def _enrich_data_with_providers(data: dict, ctx: BindContext) -> dict:
    """V1 仅注入 system provider；后续业务模块可注册自己的 provider。"""
    enriched = dict(data or {})
    for name, provider in ProviderRegistry.all().items():
        try:
            payload = await provider.provide(ctx)
            # system → 顶层；其他 namespace 拼成 _provider_<name>
            if name == "system":
                enriched.update(payload)
            else:
                enriched[f"_{name}"] = payload
        except Exception as e:  # provider 出错不阻塞主流程
            logger.warning(f"[UDPE] provider '{name}' failed: {e}")
    return enriched


async def _resolve_business_data(
    doc_type: str, identifier: Any, ctx: BindContext,
) -> dict:
    """V1: 走 ResolverRegistry；找不到就降级用 req.data 透传。"""
    resolver = ResolverRegistry.get(doc_type)
    if not resolver:
        logger.debug(f"[UDPE] no resolver for doc_type={doc_type}, pass-through data")
        return {}
    try:
        return await resolver.resolve(identifier, ctx)
    except Exception as e:
        raise PrintDataResolveError(f"Resolver '{doc_type}' 失败: {e}") from e


async def render_by_schema(
    db: AsyncSession,
    doc_type: str,
    schema_json: dict,
    req_data: dict,
    options: dict,
    bind_ctx,
) -> PrintResult:
    """M3 阶段 1: 编辑器实时预览. 不依赖已保存的 templateCode, 直接用传入的 schema.

    流程同 render(), 但跳过 get_active_template_by_code, 直接用 schema_json.
    不写 print_logs (预览而已, 不污染日志).
    """
    from app.core.print import RendererRegistry, RenderContext
    started = time.time()
    schema = schema_json or {}
    doc_type = doc_type or ""

    opts = options or {}
    render_mode = (opts.get("renderMode") or "html") if isinstance(opts, dict) else "html"

    # 1) VariableProvider
    data = await _enrich_data_with_providers(req_data or {}, bind_ctx)

    # 2) Resolver (兼容 _resolver / sourceId)
    resolver_id = data.pop("_resolver", None) if isinstance(data, dict) else None
    source_id = (opts.get("sourceId") or None) if isinstance(opts, dict) else None
    if resolver_id is not None or (source_id and doc_type):
        bind_ctx.extra["db"] = db
        rid = resolver_id if resolver_id is not None else source_id
        biz_data = await _resolve_business_data(doc_type, rid, bind_ctx)
        data.update(biz_data)

    # 3) Renderer
    renderer_name = render_mode
    renderer = RendererRegistry.get(renderer_name)
    template_for_renderer = {
        "code": "editor_preview",
        "name": "editor_preview",
        "docType": doc_type,
        "version": 0,
        **schema,
    }
    render_ctx = RenderContext(
        render_mode=render_mode,
        copies=1,
        watermark=None,
        filename=f"preview.{ 'pdf' if render_mode == 'pdf' else 'html' }",
        options=opts if isinstance(opts, dict) else {},
        bind_ctx=bind_ctx,
    )
    content_bytes = await renderer.render(template_for_renderer, data, render_ctx)
    elapsed = int((time.time() - started) * 1000)
    return PrintResult(
        content=content_bytes,
        filename=render_ctx.filename or "preview.html",
        mime_type=renderer.mime_type,
        log_id=0,  # 编辑器预览不写日志
        template_id=0,
        renderer_name=renderer_name,
        elapsed_ms=elapsed,
    )


async def render(
    db: AsyncSession,
    req: PrintRequest,
    bind_ctx: BindContext,
) -> PrintResult:
    """统一渲染入口（M1 阶段 3 完整版）。

    流程：
      1) 加载模板（走缓存）
      2) 注入 VariableProvider（system 等）
      3) 调 Resolver 取业务数据（如果有 _resolver 字段或 doc_type 走 ResolverRegistry）
      4) 调 Renderer.render(template, data, render_ctx) → bytes
      5) 写 print_logs
    """
    started = time.time()
    template_dict = await get_active_template_by_code(db, req.template_code, use_cache=True)
    schema = template_dict.get("schema_json") or {}
    doc_type = template_dict.get("doc_type") or ""

    # options → render_mode / watermark
    opts = req.options or {}
    render_mode = (opts.get("renderMode") or "pdf") if isinstance(opts, dict) else "pdf"
    copies = (opts.get("copies") or 1) if isinstance(opts, dict) else 1
    watermark = (opts.get("watermark") or None) if isinstance(opts, dict) else None
    source_module = (opts.get("sourceModule") or None) if isinstance(opts, dict) else None
    source_id = (opts.get("sourceId") or None) if isinstance(opts, dict) else None

    # 1) VariableProvider 注入
    data = await _enrich_data_with_providers(req.data or {}, bind_ctx)

    # 2) Resolver 取业务数据（如果有 _resolver 字段标识）
    resolver_id = data.pop("_resolver", None) if isinstance(data, dict) else None
    if resolver_id is not None:
        bind_ctx.extra["db"] = db
        biz_data = await _resolve_business_data(doc_type, resolver_id, bind_ctx)
        data.update(biz_data)
    elif source_id and doc_type:
        # 兼容：上层把 sourceId 传过来时，自动走 Resolver
        bind_ctx.extra["db"] = db
        biz_data = await _resolve_business_data(doc_type, source_id, bind_ctx)
        data.update(biz_data)

    # 3) Renderer 渲染
    renderer_name = render_mode  # "pdf" | "html"
    try:
        renderer = RendererRegistry.get(renderer_name)
    except Exception as e:
        raise PrintRenderError(f"Renderer '{renderer_name}' 不可用: {e}") from e

    # 把模板 schema 摊平为 renderer 期待的 dict（schema_json 整体作为 template）
    template_for_renderer = {
        "code": template_dict.get("code"),
        "name": template_dict.get("name"),
        "docType": doc_type,
        "version": template_dict.get("version"),
        **schema,  # body / meta / paper / marginMm
    }
    render_ctx = RenderContext(
        render_mode=render_mode,
        copies=copies,
        watermark=watermark,
        filename=f"{template_dict.get('code')}.{ 'pdf' if render_mode == 'pdf' else 'html' }",
        options=opts if isinstance(opts, dict) else {},
        bind_ctx=bind_ctx,
    )
    # bind_ctx 也挂上 db，方便 provider/resolver 自取
    bind_ctx.extra.setdefault("db", db)

    try:
        content = await renderer.render(template_for_renderer, data, render_ctx)
    except Exception as e:
        # 失败也要写日志
        await _write_log(
            db, template_dict, render_mode, "failed", bind_ctx,
            elapsed_ms=int((time.time() - started) * 1000),
            error_msg=str(e)[:500], request_data=req.data, source_module=source_module, source_id=source_id,
            pdf_size=None,
        )
        raise PrintRenderError(f"渲染失败（{template_dict.get('code')}）: {e}") from e

    elapsed = int((time.time() - started) * 1000)
    log = await _write_log(
        db, template_dict, render_mode, "success", bind_ctx,
        elapsed_ms=elapsed, error_msg=None, request_data=req.data,
        source_module=source_module, source_id=source_id,
        pdf_size=len(content) if render_mode == "pdf" else None,
    )

    return PrintResult(
        content=content,
        filename=render_ctx.filename or f"{template_dict.get('code')}.pdf",
        mime_type=renderer.mime_type,
        log_id=log.id,
        template_id=template_dict.get("id", 0),
        renderer_name=renderer_name,
        elapsed_ms=elapsed,
    )


async def _write_log(
    db, template_dict: dict, render_mode: str, status: str, bind_ctx: BindContext,
    *, elapsed_ms: int, error_msg: Optional[str], request_data: Optional[dict],
    source_module: Optional[str], source_id: Optional[str], pdf_size: Optional[int],
) -> PrintLog:
    log = PrintLog(
        template_id=template_dict.get("id"),
        template_code=template_dict.get("code") or "",
        doc_type=template_dict.get("doc_type") or "",
        action=render_mode,
        status=status,
        operator_id=bind_ctx.operator_id,
        operator_name=bind_ctx.operator_name,
        source_module=source_module or bind_ctx.source_module,
        source_id=source_id or bind_ctx.source_id,
        elapsed_ms=elapsed_ms,
        error_msg=error_msg,
        pdf_size=pdf_size,
        request_data=request_data,  # 评审决策 #5：完整快照，不脱敏
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


# ===== 日志查询 =====

async def list_logs(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 50,
    template_code: Optional[str] = None,
    operator_id: Optional[int] = None,
) -> tuple[list[PrintLog], int]:
    q = select(PrintLog)
    count_q = select(func.count()).select_from(PrintLog)
    if template_code:
        q = q.where(PrintLog.template_code == template_code)
        count_q = count_q.where(PrintLog.template_code == template_code)
    if operator_id is not None:
        q = q.where(PrintLog.operator_id == operator_id)
        count_q = count_q.where(PrintLog.operator_id == operator_id)
    total = (await db.execute(count_q)).scalar() or 0
    q = q.order_by(PrintLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    return list(rows), total


# ===== M2 阶段 9: 批量渲染 =====

import io
import time
from typing import List, Tuple

async def render_batch(
    db: AsyncSession,
    template_code: str,
    item_ids: List,
    bind_ctx,
) -> Tuple[bytes, List[int], List[dict], int]:
    """批量渲染并合并为单个 PDF (M2 阶段 9).

    Args:
        db: 数据库 session
        template_code: 模板 code
        item_ids: 业务主键列表 (string/number 混合)
        bind_ctx: BindContext (含 operator_id, source_module 等)

    Returns:
        (merged_pdf_bytes, log_ids, failed_items, elapsed_ms)
    """
    started = time.time()
    log_ids: List[int] = []
    failed_items: List[dict] = []
    pdf_chunks: List[bytes] = []

    # bind_ctx 注入 db (与 service.render 保持一致,供 Resolver/Provider 使用)
    bind_ctx.extra["db"] = db

    # 1) 顺序渲染 (避免 db session 竞争). V1 不上并发,后续可改 asyncio.Semaphore
    for item_id in item_ids:
        try:
            req = PrintRequest(
                template_code=template_code,
                data={"_resolver": item_id},
                options={
                    "renderMode": "pdf",
                    "sourceModule": bind_ctx.source_module or "",
                    "sourceId": str(item_id),
                },
            )
            result = await render(db, req, bind_ctx)
            pdf_chunks.append(result.content)
            log_ids.append(result.log_id)
        except Exception as e:
            failed_items.append({"id": str(item_id), "error": str(e)[:200]})

    # 2) 用 pymupdf 合并所有 PDF
    if not pdf_chunks:
        raise PrintRenderError("批量渲染全部失败, 无可合并内容")

    merged = _merge_pdfs(pdf_chunks)
    elapsed = int((time.time() - started) * 1000)
    return merged, log_ids, failed_items, elapsed


def _merge_pdfs(pdf_chunks: List[bytes]) -> bytes:
    """用 pymupdf 合并多个 PDF bytes (M2 阶段 9).

    复用 PyMuPDF (fitz) 1.27, 无需新增 pypdf 依赖.
    """
    import fitz  # PyMuPDF
    merged_doc = fitz.open()
    try:
        for chunk in pdf_chunks:
            src = fitz.open(stream=chunk, filetype="pdf")
            try:
                merged_doc.insert_pdf(src)
            finally:
                src.close()
        buf = io.BytesIO()
        merged_doc.save(buf)
        return buf.getvalue()
    finally:
        merged_doc.close()
