"""
发票打印工作台路由
- 模板 CRUD、拼版预览、PDF 生成、批量打印、打印历史
"""
import math
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, get_current_user, require_permission
from app.core.exceptions import NotFoundException, ParamErrorException
from app.modules.invoice_print.models import (
    InvoicePrintTemplate,
    InvoicePrintHistory,
)
from app.modules.invoice_ocr.models import Invoice
from app.modules.common.models import File

logger = logging.getLogger(__name__)

router = APIRouter()


# ===== Pydantic 请求体 =====

class TemplateCreateBody(BaseModel):
    """创建/更新打印模板"""
    name: str
    paper: str = "A4"
    orientation: str = "portrait"
    marginTop: int = 10
    marginRight: int = 10
    marginBottom: int = 10
    marginLeft: int = 10
    layoutCols: int = 1
    layoutRows: int = 1
    scaleMode: str = "fit"
    autoRotate: bool = True
    autoCenter: bool = True
    headerText: Optional[str] = None
    footerText: Optional[str] = None
    showQrcodeMargin: bool = True
    configJson: Optional[dict] = None


class PreviewBody(BaseModel):
    """打印预览请求"""
    invoiceIds: list[int]
    templateId: Optional[int] = None
    template: Optional[dict] = None  # 前端临时模板参数（未保存时使用）


class LayoutBody(BaseModel):
    """拼版计算请求"""
    invoiceCount: int
    templateId: Optional[int] = None
    template: Optional[dict] = None


class BatchPrintBody(BaseModel):
    """批量打印请求"""
    invoiceIds: list[int]
    templateId: Optional[int] = None
    mode: str = "layout"  # single/layout/pdf
    copies: int = 1


# ===== 辅助函数 =====

# 纸张尺寸映射（mm）
PAPER_SIZES = {
    "A3": (297, 420),
    "A4": (210, 297),
    "A5": (148, 210),
    "Letter": (215.9, 279.4),
}


async def _get_template_or_dict(
    db: AsyncSession, template_id: Optional[int], template_param: Optional[dict],
) -> dict:
    """获取模板配置：优先用已有模板 ID，否则用前端传入的临时参数。"""
    if template_id:
        t = (
            await db.execute(
                select(InvoicePrintTemplate).where(InvoicePrintTemplate.id == template_id)
            )
        ).scalar_one_or_none()
        if not t:
            raise NotFoundException(f"打印模板不存在：{template_id}")
        return t.to_dict()
    if template_param:
        return template_param
    # 默认 A4 单张
    return {
        "paper": "A4", "orientation": "portrait",
        "marginTop": 10, "marginRight": 10, "marginBottom": 10, "marginLeft": 10,
        "layoutCols": 1, "layoutRows": 1, "scaleMode": "fit",
        "autoRotate": True, "autoCenter": True,
        "headerText": None, "footerText": None,
        "showQrcodeMargin": True,
    }


def _calc_layout(tpl: dict, invoice_count: int) -> dict:
    """
    计算拼版布局。
    返回 { pages, totalInvoices, layoutCols, layoutRows, pagesDetail: [...] }
    每页 detail 包含该页的发票索引列表和各位置坐标。
    """
    cols = max(1, int(tpl.get("layoutCols", 1)))
    rows = max(1, int(tpl.get("layoutRows", 1)))
    per_page = cols * rows

    paper = tpl.get("paper", "A4")
    orientation = tpl.get("orientation", "portrait")
    pw, ph = PAPER_SIZES.get(paper, PAPER_SIZES["A4"])
    if orientation == "landscape":
        pw, ph = ph, pw

    mt = int(tpl.get("marginTop", 10))
    mr = int(tpl.get("marginRight", 10))
    mb = int(tpl.get("marginBottom", 10))
    ml = int(tpl.get("marginLeft", 10))

    # 可用区域（mm）
    avail_w = pw - ml - mr
    avail_h = ph - mt - mb
    cell_w = avail_w / cols
    cell_h = avail_h / rows

    total_pages = math.ceil(invoice_count / per_page) if invoice_count > 0 else 0
    pages_detail = []
    for page_idx in range(total_pages):
        items = []
        for slot in range(per_page):
            inv_idx = page_idx * per_page + slot
            if inv_idx >= invoice_count:
                break
            col = slot % cols
            row = slot // cols
            items.append({
                "invoiceIndex": inv_idx,
                "slot": slot,
                "col": col,
                "row": row,
                "x": round(ml + col * cell_w, 2),  # mm
                "y": round(mt + row * cell_h, 2),
                "width": round(cell_w, 2),
                "height": round(cell_h, 2),
            })
        pages_detail.append({
            "page": page_idx + 1,
            "items": items,
        })

    return {
        "pages": total_pages,
        "totalInvoices": invoice_count,
        "layoutCols": cols,
        "layoutRows": rows,
        "perPage": per_page,
        "paper": paper,
        "orientation": orientation,
        "paperWidth": pw,
        "paperHeight": ph,
        "availWidth": round(avail_w, 2),
        "availHeight": round(avail_h, 2),
        "cellWidth": round(cell_w, 2),
        "cellHeight": round(cell_h, 2),
        "pagesDetail": pages_detail,
    }


def _build_preview_html(tpl: dict, invoices: list[dict], layout: dict) -> str:
    """
    根据模板和发票列表生成拼版预览 HTML。
    每页一个 div，内部按 layout 排列发票图片。
    """
    paper = layout.get("paper", "A4")
    orientation = layout.get("orientation", "portrait")
    pw = layout.get("paperWidth", 210)
    ph = layout.get("paperHeight", 297)

    # 构建发票 id→信息映射
    inv_map = {inv["id"]: inv for inv in invoices}

    pages_html = []
    for page_info in layout.get("pagesDetail", []):
        cells_html = []
        for item in page_info.get("items", []):
            inv = invoices[item["invoiceIndex"]] if item["invoiceIndex"] < len(invoices) else None
            if not inv:
                continue
            img_url = inv.get("fileUrl", "")
            x = item["x"]
            y = item["y"]
            w = item["width"]
            h = item["height"]
            cells_html.append(
                f'<div class="cell" style="left:{x}mm;top:{y}mm;width:{w}mm;height:{h}mm;">'
                f'<img src="{img_url}" style="max-width:100%;max-height:100%;object-fit:contain;" />'
                f'</div>'
            )

        # 页眉
        header_html = ""
        header_text = tpl.get("headerText")
        if header_text:
            header_html = f'<div class="header">{header_text}</div>'

        # 页脚
        footer_html = ""
        footer_text = tpl.get("footerText")
        if footer_text:
            footer_html = f'<div class="footer">{footer_text}</div>'

        pages_html.append(
            f'<div class="page" style="width:{pw}mm;height:{ph}mm;position:relative;overflow:hidden;">'
            f'{header_html}'
            f'{"".join(cells_html)}'
            f'{footer_html}'
            f'</div>'
        )

    mt = tpl.get("marginTop", 10)
    mr = tpl.get("marginRight", 10)
    mb = tpl.get("marginBottom", 10)
    ml = tpl.get("marginLeft", 10)

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<title>发票打印预览</title>
<style>
  @page {{ size: {paper} {orientation}; margin: 0; }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif; }}
  .page {{
    page-break-after: always;
    padding: {mt}mm {mr}mm {mb}mm {ml}mm;
    background: #fff;
    position: relative;
  }}
  .cell {{
    position: absolute;
    border: 1px dashed #e0e0e0;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }}
  .header {{
    text-align: center;
    font-size: 12px;
    color: #666;
    padding-bottom: 4mm;
  }}
  .footer {{
    position: absolute;
    bottom: {mb}mm;
    left: {ml}mm;
    right: {mr}mm;
    text-align: center;
    font-size: 10px;
    color: #999;
  }}
</style>
</head>
<body>
{"".join(pages_html)}
</body>
</html>"""
    return html


# ===== 模板 CRUD =====

@router.get("/templates", summary="打印模板列表")
async def list_templates(
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """查询系统+自建模板列表"""
    q = select(InvoicePrintTemplate)
    count_q = select(func.count(InvoicePrintTemplate.id))

    if keyword:
        like = f"%{keyword}%"
        q = q.where(InvoicePrintTemplate.name.ilike(like))
        count_q = count_q.where(InvoicePrintTemplate.name.ilike(like))

    total = (await db.execute(count_q)).scalar() or 0
    rows = (
        await db.execute(
            q.order_by(
                InvoicePrintTemplate.is_system.desc(),
                InvoicePrintTemplate.is_favorite.desc(),
                desc(InvoicePrintTemplate.updated_at),
            )
            .offset((page - 1) * pageSize)
            .limit(pageSize)
        )
    ).scalars().all()

    return {
        "code": 0,
        "data": {
            "list": [t.to_dict() for t in rows],
            "total": total,
            "page": page,
            "pageSize": pageSize,
        },
    }


@router.post("/template", summary="创建打印模板")
async def create_template(
    body: TemplateCreateBody,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoice:print:template:write")),
):
    t = InvoicePrintTemplate(
        name=body.name,
        paper=body.paper,
        orientation=body.orientation,
        margin_top=body.marginTop,
        margin_right=body.marginRight,
        margin_bottom=body.marginBottom,
        margin_left=body.marginLeft,
        layout_cols=body.layoutCols,
        layout_rows=body.layoutRows,
        scale_mode=body.scaleMode,
        auto_rotate=body.autoRotate,
        auto_center=body.autoCenter,
        header_text=body.headerText,
        footer_text=body.footerText,
        show_qrcode_margin=body.showQrcodeMargin,
        config_json=body.configJson,
        creator_id=current_user.id,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return {"code": 0, "data": t.to_dict()}


@router.put("/template/{tid}", summary="更新打印模板")
async def update_template(
    tid: int,
    body: TemplateCreateBody,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoice:print:template:write")),
):
    t = (
        await db.execute(
            select(InvoicePrintTemplate).where(InvoicePrintTemplate.id == tid)
        )
    ).scalar_one_or_none()
    if not t:
        raise NotFoundException(f"打印模板不存在：{tid}")
    # 系统模板不允许修改
    if t.is_system and not current_user.is_admin:
        raise ParamErrorException("系统预设模板不允许修改")

    t.name = body.name
    t.paper = body.paper
    t.orientation = body.orientation
    t.margin_top = body.marginTop
    t.margin_right = body.marginRight
    t.margin_bottom = body.marginBottom
    t.margin_left = body.marginLeft
    t.layout_cols = body.layoutCols
    t.layout_rows = body.layoutRows
    t.scale_mode = body.scaleMode
    t.auto_rotate = body.autoRotate
    t.auto_center = body.autoCenter
    t.header_text = body.headerText
    t.footer_text = body.footerText
    t.show_qrcode_margin = body.showQrcodeMargin
    t.config_json = body.configJson
    t.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(t)
    return {"code": 0, "data": t.to_dict()}


@router.delete("/template/{tid}", summary="删除打印模板")
async def delete_template(
    tid: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoice:print:template:write")),
):
    t = (
        await db.execute(
            select(InvoicePrintTemplate).where(InvoicePrintTemplate.id == tid)
        )
    ).scalar_one_or_none()
    if not t:
        raise NotFoundException(f"打印模板不存在：{tid}")
    if t.is_system and not current_user.is_admin:
        raise ParamErrorException("系统预设模板不允许删除")

    await db.delete(t)
    await db.commit()
    return {"code": 0, "data": {"id": tid}}


# ===== 打印预览 =====

@router.post("/preview", summary="生成拼版预览 HTML")
async def preview(
    body: PreviewBody,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """根据模板和发票列表，生成拼版预览 HTML。"""
    if not body.invoiceIds:
        raise ParamErrorException("至少选择一张发票")

    # 查询发票
    invoices_orm = (
        await db.execute(
            select(Invoice).where(Invoice.id.in_(body.invoiceIds))
        )
    ).scalars().all()

    if not invoices_orm:
        raise NotFoundException("未找到选中的发票")

    # 查询关联文件 URL
    invoice_data = []
    for inv in invoices_orm:
        file_url = inv.file_url or ""
        # 如果 invoice 有 file_id，尝试查 files 表获取更准确的 URL
        if inv.file_id:
            f = (
                await db.execute(select(File).where(File.id == inv.file_id))
            ).scalar_one_or_none()
            if f:
                file_url = f.url
        invoice_data.append({
            "id": inv.id,
            "invoiceNo": inv.invoice_no,
            "invoiceCode": inv.invoice_code,
            "fileUrl": file_url,
            "fileId": inv.file_id,
            "invoiceType": inv.invoice_type,
            "sellerName": inv.seller_name,
            "buyerName": inv.buyer_name,
            "totalAmount": inv.total_amount,
        })

    # 获取模板配置
    tpl = await _get_template_or_dict(db, body.templateId, body.template)

    # 计算拼版
    layout = _calc_layout(tpl, len(invoice_data))

    # 生成 HTML
    html = _build_preview_html(tpl, invoice_data, layout)

    return {
        "code": 0,
        "data": {
            "html": html,
            "layout": layout,
            "invoiceCount": len(invoice_data),
        },
    }


# ===== PDF 生成 =====

@router.post("/pdf", summary="生成打印 PDF")
async def generate_pdf(
    body: PreviewBody,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    生成 PDF：先生成预览 HTML，再用 WeasyPrint 转换。
    返回 PDF 文件的 base64 编码（前端可直接下载）。
    """
    import base64

    if not body.invoiceIds:
        raise ParamErrorException("至少选择一张发票")

    # 复用 preview 逻辑获取发票数据和模板
    invoices_orm = (
        await db.execute(
            select(Invoice).where(Invoice.id.in_(body.invoiceIds))
        )
    ).scalars().all()
    if not invoices_orm:
        raise NotFoundException("未找到选中的发票")

    invoice_data = []
    for inv in invoices_orm:
        file_url = inv.file_url or ""
        if inv.file_id:
            f = (
                await db.execute(select(File).where(File.id == inv.file_id))
            ).scalar_one_or_none()
            if f:
                file_url = f.url
        invoice_data.append({
            "id": inv.id,
            "invoiceNo": inv.invoice_no,
            "invoiceCode": inv.invoice_code,
            "fileUrl": file_url,
            "fileId": inv.file_id,
            "invoiceType": inv.invoice_type,
            "sellerName": inv.seller_name,
            "buyerName": inv.buyer_name,
            "totalAmount": inv.total_amount,
        })

    tpl = await _get_template_or_dict(db, body.templateId, body.template)
    layout = _calc_layout(tpl, len(invoice_data))
    html = _build_preview_html(tpl, invoice_data, layout)

    # 用 WeasyPrint 转 PDF
    pdf_bytes = b""
    pdf_error = None
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html).write_pdf()
    except ImportError:
        pdf_error = "WeasyPrint 未安装，无法生成 PDF"
        logger.warning(pdf_error)
    except Exception as e:
        pdf_error = f"PDF 生成失败：{e}"
        logger.exception("PDF 生成异常")

    if pdf_error:
        return {
            "code": 1,
            "message": pdf_error,
            "data": {"html": html, "layout": layout},
        }

    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    return {
        "code": 0,
        "data": {
            "pdfBase64": pdf_base64,
            "size": len(pdf_bytes),
            "pageCount": layout.get("pages", 0),
            "invoiceCount": len(invoice_data),
        },
    }


# ===== 拼版计算 =====

@router.post("/layout", summary="拼版布局计算")
async def calc_layout(
    body: LayoutBody,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """根据模板和发票数量，计算分页布局和每页坐标。"""
    if body.invoiceCount < 1:
        raise ParamErrorException("发票数量至少为 1")

    tpl = await _get_template_or_dict(db, body.templateId, body.template)
    layout = _calc_layout(tpl, body.invoiceCount)

    return {"code": 0, "data": layout}


# ===== 批量打印 =====

@router.post("/batch", summary="批量打印")
async def batch_print(
    body: BatchPrintBody,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoice:print:batch")),
):
    """
    批量打印：逐条写入打印历史。
    返回成功/失败统计。
    """
    if not body.invoiceIds:
        raise ParamErrorException("至少选择一张发票")

    # 获取模板名称
    tpl_name = "默认模板"
    if body.templateId:
        t = (
            await db.execute(
                select(InvoicePrintTemplate).where(InvoicePrintTemplate.id == body.templateId)
            )
        ).scalar_one_or_none()
        if t:
            tpl_name = t.name

    # 查询发票
    invoices_orm = (
        await db.execute(
            select(Invoice).where(Invoice.id.in_(body.invoiceIds))
        )
    ).scalars().all()

    inv_map = {inv.id: inv for inv in invoices_orm}

    success_count = 0
    fail_count = 0
    history_ids = []

    for inv_id in body.invoiceIds:
        inv = inv_map.get(inv_id)
        try:
            if not inv:
                raise Exception(f"发票不存在：{inv_id}")

            # 拼版描述
            layout_desc = None
            if body.mode == "layout" and body.templateId:
                tpl = await _get_template_or_dict(db, body.templateId, None)
                layout_desc = f"{tpl.get('layoutCols', 1)}x{tpl.get('layoutRows', 1)}"

            h = InvoicePrintHistory(
                invoice_id=inv.id,
                invoice_no=inv.invoice_no,
                template_id=body.templateId,
                template_name=tpl_name,
                mode=body.mode,
                layout_desc=layout_desc,
                copies=body.copies,
                status="success",
                operator_id=current_user.id,
                operator_name=current_user.name,
            )
            db.add(h)
            await db.flush()
            history_ids.append(h.id)
            success_count += 1
        except Exception as e:
            # 写失败记录
            h = InvoicePrintHistory(
                invoice_id=inv_id,
                invoice_no=inv.invoice_no if inv else None,
                template_id=body.templateId,
                template_name=tpl_name,
                mode=body.mode,
                copies=body.copies,
                status="failed",
                error_msg=str(e),
                operator_id=current_user.id,
                operator_name=current_user.name,
            )
            db.add(h)
            await db.flush()
            history_ids.append(h.id)
            fail_count += 1

    await db.commit()

    return {
        "code": 0,
        "data": {
            "success": success_count,
            "failed": fail_count,
            "total": len(body.invoiceIds),
            "historyIds": history_ids,
        },
    }


# ===== 打印历史 =====

@router.get("/history", summary="打印历史查询")
async def list_history(
    invoiceId: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    startDate: Optional[str] = Query(None),
    endDate: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    pageSize: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """查询打印历史，支持按发票、状态、时间范围过滤。"""
    q = select(InvoicePrintHistory)
    count_q = select(func.count(InvoicePrintHistory.id))

    if invoiceId:
        q = q.where(InvoicePrintHistory.invoice_id == invoiceId)
        count_q = count_q.where(InvoicePrintHistory.invoice_id == invoiceId)
    if status:
        q = q.where(InvoicePrintHistory.status == status)
        count_q = count_q.where(InvoicePrintHistory.status == status)
    if startDate:
        try:
            dt = datetime.fromisoformat(startDate)
            q = q.where(InvoicePrintHistory.printed_at >= dt)
            count_q = count_q.where(InvoicePrintHistory.printed_at >= dt)
        except ValueError:
            pass
    if endDate:
        try:
            dt = datetime.fromisoformat(endDate)
            q = q.where(InvoicePrintHistory.printed_at <= dt)
            count_q = count_q.where(InvoicePrintHistory.printed_at <= dt)
        except ValueError:
            pass

    total = (await db.execute(count_q)).scalar() or 0
    rows = (
        await db.execute(
            q.order_by(desc(InvoicePrintHistory.printed_at))
            .offset((page - 1) * pageSize)
            .limit(pageSize)
        )
    ).scalars().all()

    return {
        "code": 0,
        "data": {
            "list": [h.to_dict() for h in rows],
            "total": total,
            "page": page,
            "pageSize": pageSize,
        },
    }


# ===== 种子模板 =====

@router.post("/seed-templates", summary="创建系统预设模板")
async def seed_templates(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("invoice:print:template:write")),
):
    """
    创建系统预设的打印模板（幂等：如果已存在则跳过）。
    预设包括：A4 单张、A4 双栏、A4 四格、A5 单张等。
    """
    presets = [
        {
            "name": "A4 标准单张",
            "paper": "A4",
            "orientation": "portrait",
            "layout_cols": 1,
            "layout_rows": 1,
            "margin_top": 15,
            "margin_right": 15,
            "margin_bottom": 15,
            "margin_left": 15,
            "scale_mode": "fit",
            "auto_rotate": True,
            "auto_center": True,
            "header_text": None,
            "footer_text": None,
            "show_qrcode_margin": True,
            "is_system": True,
        },
        {
            "name": "A4 横向单张",
            "paper": "A4",
            "orientation": "landscape",
            "layout_cols": 1,
            "layout_rows": 1,
            "margin_top": 10,
            "margin_right": 10,
            "margin_bottom": 10,
            "margin_left": 10,
            "scale_mode": "fit",
            "auto_rotate": True,
            "auto_center": True,
            "header_text": None,
            "footer_text": None,
            "show_qrcode_margin": True,
            "is_system": True,
        },
        {
            "name": "A4 双栏拼版",
            "paper": "A4",
            "orientation": "portrait",
            "layout_cols": 2,
            "layout_rows": 1,
            "margin_top": 10,
            "margin_right": 10,
            "margin_bottom": 10,
            "margin_left": 10,
            "scale_mode": "fit",
            "auto_rotate": True,
            "auto_center": True,
            "header_text": None,
            "footer_text": None,
            "show_qrcode_margin": True,
            "is_system": True,
        },
        {
            "name": "A4 四格拼版",
            "paper": "A4",
            "orientation": "portrait",
            "layout_cols": 2,
            "layout_rows": 2,
            "margin_top": 8,
            "margin_right": 8,
            "margin_bottom": 8,
            "margin_left": 8,
            "scale_mode": "fit",
            "auto_rotate": True,
            "auto_center": True,
            "header_text": None,
            "footer_text": None,
            "show_qrcode_margin": False,
            "is_system": True,
        },
        {
            "name": "A5 标准单张",
            "paper": "A5",
            "orientation": "portrait",
            "layout_cols": 1,
            "layout_rows": 1,
            "margin_top": 10,
            "margin_right": 10,
            "margin_bottom": 10,
            "margin_left": 10,
            "scale_mode": "fit",
            "auto_rotate": True,
            "auto_center": True,
            "header_text": None,
            "footer_text": None,
            "show_qrcode_margin": True,
            "is_system": True,
        },
    ]

    created = 0
    skipped = 0
    for preset in presets:
        exists = (
            await db.execute(
                select(InvoicePrintTemplate).where(
                    InvoicePrintTemplate.name == preset["name"],
                    InvoicePrintTemplate.is_system == True,
                )
            )
        ).scalar_one_or_none()
        if exists:
            skipped += 1
            continue

        t = InvoicePrintTemplate(
            creator_id=current_user.id,
            **preset,
        )
        db.add(t)
        created += 1

    await db.commit()

    return {
        "code": 0,
        "data": {
            "created": created,
            "skipped": skipped,
            "total": len(presets),
        },
    }
