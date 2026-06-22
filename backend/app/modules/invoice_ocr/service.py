"""
发票识别服务
- 单张 OCR 识别 + 入库
- 批量上传 + 异步处理 + SSE 推送
"""
import asyncio
import random
import string
import uuid
import re
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException, ParamErrorException, ConflictException, OCRFailedException
from app.core.sse import (
    publish_batch_progress, publish_batch_item_done,
    publish_batch_summary, publish_batch_completed,
)
from app.modules.invoice_ocr.models import (
    Invoice, InvoiceBatchTask, InvoiceBatchItem, InvoiceRelation,
)
from app.modules.auth.models import User
from app.integrations import ocr_client
from app.integrations import image_converter
from app.core.exceptions import OCRFailedException


def _gen_invoice_code() -> str:
    return f"INV-{datetime.now().strftime('%Y-%m-%d')}-{uuid.uuid4().hex[:3].upper()}"


def _gen_batch_code() -> str:
    return f"BATCH-{datetime.now().strftime('%Y-%m-%d')}-{uuid.uuid4().hex[:3].upper()}"


def _parse_issue_date(s):
    """把 YYYY-MM-DD / YYYY/MM/DD / YYYYMMDD / datetime 解析为 date"""
    if not s:
        return None
    txt = str(s)[:10]
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            return datetime.strptime(txt, fmt).date()
        except Exception:
            pass
    return None



async def _save_file(filename: str, content: bytes) -> dict:
    """
    OCR 转码回调：把转码后的 jpeg 存到 storage
    返回 {"url": "...", "filename": "...", "size": int}
    """
    from app.integrations.storage import save_file
    return await save_file(filename, content)


def _flatten_ocr_response(ocr: dict) -> dict:
    """
    把新 ocr_client 协议（fields 嵌套）→ 还原成旧 flat 结构（service 老代码读旧字段）
    返回字段：invoiceType, invoiceCode, invoiceNo, issueDate,
             sellerName, sellerTaxNo, buyerName, buyerTaxNo,
             totalAmountCents, taxAmountCents, amountExclTaxCents,
             totalAmountCn, taxRate, confidence, status, items
    """
    fields = ocr.get("fields", {}) if isinstance(ocr.get("fields"), dict) else {}

    def _f(k):
        v = fields.get(k)
        if isinstance(v, dict):
            return v.get("value")
        return v

    def _y2c(v):
        if v is None:
            return 0
        try:
            return int(Decimal(str(v)) * 100)
        except Exception:
            return 0

    return {
        "invoiceType": _f("invoiceType") or "电子普通发票",
        "invoiceCode": _f("invoiceCode") or "",
        "invoiceNo": _f("invoiceNo") or "",
        "issueDate": _f("issueDate") or date.today().isoformat(),
        "sellerName": _f("sellerName") or "",
        "sellerTaxNo": _f("sellerTaxNo") or "",
        "buyerName": _f("buyerName") or "",
        "buyerTaxNo": _f("buyerTaxNo") or "",
        "totalAmountCents": _y2c(_f("totalAmount")),
        "taxAmountCents": _y2c(_f("taxAmount")),
        "amountExclTaxCents": _y2c(_f("amount")),
        "totalAmountCn": _f("totalAmountCn") or "",
        "verifyCode": _f("verifyCode") or "",
        "remarks": _f("remarks") or "",
        "taxRate": _f("taxRate") or 0,
        "confidence": ocr.get("confidence", 0),
        "status": ocr.get("status", "verified"),
        "items": ocr.get("items", []),
    }


# ===== 单张识别 =====

async def recognize_one(
    db: AsyncSession,
    file_id: str,
    file_url: str,
    uploader_id: int,
    file_size: Optional[int] = None,
    template_id: Optional[int] = None,
) -> dict:
    """OCR 识别一张发票 + 入库"""
    # R18.1: 非标准格式（PDF/HEIC/WEBP/...）转码为 JPEG 再 OCR
    # 失败抛 OCRFailedException，调用方需要 try/except 转 failed 响应
    try:
        normalized_url, normalized_name, _ = await image_converter.normalize_to_jpeg(
            file_url=file_url,
            file_id=file_id,
            save_callback=_save_file,
        )
        if normalized_url != file_url:
            from loguru import logger
            logger.info(f"[OCR 转码] {file_url} → {normalized_name} → {normalized_url}")
            ocr_url = normalized_url
        else:
            ocr_url = file_url
    except OCRFailedException as e:
        return {
            "invoiceId": None,
            "code": None,
            "ocrStatus": "failed",
            "confidence": 0,
            "error": str(e),
            "fields": {},
            "fileUrl": file_url,
            "previewUrl": file_url,
        }

    ocr = await ocr_client.recognize(file_id, ocr_url)

    if ocr.get("status") == "failed":
        return {
            "invoiceId": None,
            "ocrStatus": "failed",
            "confidence": ocr["confidence"],
            "error": ocr.get("error", "识别失败"),
            "fileUrl": file_url,
        }

    # 适配新 ocr_client 协议（fields 嵌套 + 元数据）→ 还原成旧 flat 结构入库
    fields = ocr.get("fields", {})
    def _f(k):
        """从 fields 嵌套结构取 .value（兼容 dict 和 str 两种）"""
        v = fields.get(k)
        if isinstance(v, dict):
            return v.get("value")
        return v

    # 金额元 → 分
    def _y2c(v):
        if v is None:
            return 0
        return int(Decimal(str(v)) * 100)

    invoice_type = _f("invoiceType") or "电子普通发票"
    invoice_code = _f("invoiceCode") or ""
    invoice_no = _f("invoiceNo") or ""
    issue_date_str = _f("issueDate") or date.today().isoformat()
    seller_name = _f("sellerName") or ""
    seller_tax_no = _f("sellerTaxNo") or ""
    buyer_name = _f("buyerName") or ""
    buyer_tax_no = _f("buyerTaxNo") or ""
    total_amount_cents = _y2c(_f("totalAmount"))
    tax_amount_cents = _y2c(_f("taxAmount"))
    amount_excl_tax_cents = _y2c(_f("amount"))
    tax_rate = _f("taxRate") or 0
    # R18 修复：OCR 不返 totalAmountCn → 兜底用 _cn_capital 生成
    if not (_f("totalAmountCn")):
        from app.integrations.ocr_client import _cn_capital
        total_amount_cn = _cn_capital(Decimal(total_amount_cents) / 100) if total_amount_cents else ""
    else:
        total_amount_cn = _f("totalAmountCn")

    inv = Invoice(
        code=_gen_invoice_code(),
        invoice_type=invoice_type,
        invoice_code=invoice_code,
        invoice_no=invoice_no,
        issue_date=date.fromisoformat(issue_date_str) if isinstance(issue_date_str, str) else issue_date_str,
        seller_name=seller_name,
        seller_tax_no=seller_tax_no,
        buyer_name=buyer_name,
        buyer_tax_no=buyer_tax_no,
        total_amount=total_amount_cents,
        total_amount_cn=total_amount_cn,
        verify_code=_f("verifyCode") or _f("verify_code") or "",
        remarks=_f("remarks") or "",
        tax_rate=Decimal(str(tax_rate)),
        tax_amount=tax_amount_cents,
        amount_excl_tax=amount_excl_tax_cents,
        confidence=Decimal(str(ocr.get("confidence", 0))) * 100,  # 0-100 存
        status=ocr.get("status", "verified"),
        file_url=file_url,
        file_id=file_id,
        file_size=file_size,
        template_id=template_id,
        items=_clean_items(ocr.get("items", [])),
        raw_ocr=ocr,
        uploader_id=uploader_id,
    )
    db.add(inv)
    await db.commit()
    await db.refresh(inv)

    return {
        "invoiceId": inv.id,
        "code": inv.code,
        "ocrStatus": "success",
        "confidence": ocr.get("confidence", 0),
        "fields": {
            "invoiceType": invoice_type,
            "invoiceCode": invoice_code,
            "invoiceNo": invoice_no,
            "issueDate": issue_date_str,
            "sellerName": seller_name,
            "sellerTaxNo": seller_tax_no,
            "buyerName": buyer_name,
            "buyerTaxNo": buyer_tax_no,
            "totalAmount": float(Decimal(total_amount_cents) / 100),
            "totalAmountCn": total_amount_cn,
            "taxRate": tax_rate,
            "taxAmount": float(Decimal(tax_amount_cents) / 100),
            "amountExclTax": float(Decimal(amount_excl_tax_cents) / 100),
            "items": ocr.get("items", []),
            # AI 启发式归类（销售方名/发票类型 → 费用类型），前端可一键带入报销单
            # 仅前端入账时使用，DB 不持久化（与 Expense.category 解耦）
            "expenseType": _classify_expense_category(seller_name, invoice_type) if seller_name else "",
        },
        "fileUrl": file_url,
        # 预览图：转码后的 jpg URL（PDF/HEIC/WEBP 等被转码过；JPEG/PNG 直接用原 URL）
        # 前端 img 标签可显示，避开 PDF iframe 的兼容问题
        "previewUrl": normalized_url if normalized_url != file_url else file_url,
        "verifyStatus": "pending" if ocr.get("status") == "pending_verify" else "verified",
    }


# ===== 列表 =====

async def list_invoices(
    db: AsyncSession, page: int = 1, page_size: int = 20,
    keyword: str = "", filters: dict = None,
) -> tuple[list[dict], int]:
    filters = filters or {}
    query = select(Invoice)
    if keyword:
        query = query.where(or_(
            Invoice.invoice_no.ilike(f"%{keyword}%"),
            Invoice.code.ilike(f"%{keyword}%"),
            Invoice.seller_name.ilike(f"%{keyword}%"),
        ))
    if filters.get("type"):
        query = query.where(Invoice.invoice_type == filters["type"])
    if filters.get("status"):
        query = query.where(Invoice.status == filters["status"])
    if filters.get("dateRange"):
        dr = filters["dateRange"]
        if isinstance(dr, list) and len(dr) == 2:
            try:
                d1 = date.fromisoformat(dr[0]); d2 = date.fromisoformat(dr[1])
                query = query.where(Invoice.issue_date >= d1, Invoice.issue_date <= d2)
            except Exception:
                pass

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = query.order_by(Invoice.id.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()

    # 批量取上传人姓名（避免 N+1）
    uploader_ids = {inv.uploader_id for inv in rows if inv.uploader_id}
    uploader_map: dict[int, str] = {}
    if uploader_ids:
        from app.modules.auth.models import User
        user_rows = (await db.execute(
            select(User.id, User.name, User.username).where(User.id.in_(uploader_ids))
        )).all()
        for uid, name, username in user_rows:
            uploader_map[uid] = name or username or f"#{uid}"

    # 批量取关联（合同/项目/回款）
    invoice_ids = [inv.id for inv in rows]
    relations_map: dict[int, list] = {}
    if invoice_ids:
        from app.modules.invoice_ocr.models import InvoiceRelation
        rel_rows = (await db.execute(
            select(InvoiceRelation).where(InvoiceRelation.invoice_id.in_(invoice_ids))
        )).scalars().all()
        for r in rel_rows:
            relations_map.setdefault(r.invoice_id, []).append({
                "type": r.relation_type,  # contract / project / receivable
                "id": r.relation_id,
            })

    items = []
    for inv in rows:
        items.append({
            "invoiceId": inv.id,
            "code": inv.code,
            "invoiceType": inv.invoice_type,
            "invoiceNo": inv.invoice_no,
            "sellerName": inv.seller_name,
            "buyerName": inv.buyer_name,
            "totalAmount": Decimal(inv.total_amount or 0) / 100,
            "taxAmount": Decimal(inv.tax_amount or 0) / 100,
            "amountExclTax": Decimal(inv.amount_excl_tax or 0) / 100,
            "issueDate": inv.issue_date.isoformat() if inv.issue_date else None,
            "confidence": float(inv.confidence or 0) / 100,
            "status": inv.status,
            "verifyStatus": inv.verify_status,
            "isLinkedContract": inv.is_linked_contract,
            "isLinkedProject": inv.is_linked_project,
            "uploaderId": inv.uploader_id,
            "uploaderName": uploader_map.get(inv.uploader_id, "—"),
            "uploadedAt": inv.uploaded_at.isoformat() if inv.uploaded_at else None,
            "relations": relations_map.get(inv.id, []),
            "templateId": inv.template_id,
        })
    # items 后处理：去重 + 修正金额错位
    for it in items:
        if "items" in it:
            it["items"] = _clean_items(it["items"])
    # 状态分组计数：同时按 status 和 verifyStatus 两个维度，返回 statusCounts = {status:xxx, verify:xxx, all, ...fallback}
    # 前端 statusTabs 想看 status 维度（pending/verified/rejected/failed/submitted），
    # 旧版只用 verifyStatus 算，导致 failed/submitted 永远是 0
    stats_q_status = select(Invoice.status, func.count()).group_by(Invoice.status)
    stats_q_verify = select(Invoice.verify_status, func.count()).group_by(Invoice.verify_status)
    rows_status = (await db.execute(stats_q_status)).all()
    rows_verify = (await db.execute(stats_q_verify)).all()
    status_counts: dict = {}
    for r in rows_status:
        k = (r[0] or "pending").strip() or "pending"
        status_counts[f"status:{k}"] = r[1]
    for r in rows_verify:
        k = (r[0] or "pending").strip() or "pending"
        status_counts[f"verify:{k}"] = r[1]
    status_counts["all"] = total
    # 兼容老格式（fallback key）
    for r in rows_verify:
        k = (r[0] or "pending").strip() or "pending"
        status_counts.setdefault(k, r[1])
    return items, total, status_counts


# ===== 批量删除 =====
async def delete_invoices(db: AsyncSession, invoice_ids: list[int]) -> int:
    """
    批量删除发票（同时级联删除 invoice_relations 关联）
    返回成功删除的数量
    """
    if not invoice_ids:
        return 0
    from app.modules.invoice_ocr.models import Invoice, InvoiceRelation, InvoiceVerifyRecord
    # 先删发票查验记录（FK invoice_id → invoices.id，nullable=True）
    await db.execute(
        InvoiceVerifyRecord.__table__.delete().where(InvoiceVerifyRecord.invoice_id.in_(invoice_ids))
    )
    # 再删关联关系（FK invoice_id → invoices.id）
    await db.execute(
        InvoiceRelation.__table__.delete().where(InvoiceRelation.invoice_id.in_(invoice_ids))
    )
    # 删主表
    result = await db.execute(
        Invoice.__table__.delete().where(Invoice.id.in_(invoice_ids))
    )
    await db.commit()
    return result.rowcount or 0


# ===== 详情 =====

def _normalize_item(it: dict) -> dict:
    """统一 item 字段命名 + 兜底空值
    - price → unitPrice（前端用 unitPrice）
    - quantity 空字符串 → 1
    - 数字字段尽量转 Decimal
    """
    if not isinstance(it, dict):
        return it
    out = dict(it)
    # 字段命名兼容
    if "price" in out and "unitPrice" not in out:
        out["unitPrice"] = out["price"]
    elif "unitPrice" in out and "price" not in out:
        out["price"] = out["unitPrice"]
    if "unit" in out and "unitName" not in out:
        out["unitName"] = out["unit"]
    # 数量兜底
    q = str(out.get("quantity", "")).strip()
    if q in ("", "-", "—", "0"):
        out["quantity"] = 1
    # 字符串数字转浮点（前端好渲染）
    for k in ("unitPrice", "amount", "taxAmount"):
        v = out.get(k)
        if isinstance(v, str):
            s2 = v.replace(",", "").replace("¥", "").replace("￥", "").strip()
            try:
                out[k] = float(s2) if s2 and s2 != "-" and s2 != "—" else 0
            except ValueError:
                pass
    return out


def _clean_items(raw_items: list) -> list:
    """OCR 抽出的 items 后处理：去重、过滤干扰行、修正金额错位。
    1) 过滤空行 / 干扰行（"产品" / "携程订单:..." 等）
    2) 金额子串去重：price "1,672.64" + amount "672.64" → 合并到 price
    3) 同名行去重
    """
    if not raw_items:
        return []
    seen = set()
    out = []
    for it in raw_items:
        name = (it.get("name") or "").strip()
        if not name:
            continue
        # 干扰行：产品 / 商品 / 携程订单 / 订单号 / 购买方信息 / 备注 等
        if name in ("产品", "商品", "项目", "服务", "注", "备注"):
            continue
        if ":" in name or "：" in name:
            # "携程订单: 1128147398848591" / "购买方地址: -" / "电话: -" 等
            continue
        if any(kw in name for kw in [
            "订单号", "PNR", "票号", "行程单", "携程",
            "购买方", "销售方", "地址", "电话", "电话:", "电话：",
            "开户银行", "银行账号", "账号", "纳税人识别号",
            "价税合计", "大写", "小写", "开票人", "收款人", "复核",
            "校验码", "发票代码", "发票号码",
        ]):
            continue
        # 纯冒号/破折号/长数字
        if re.fullmatch(r'[-—:\s\d,.一-鿿]{0,15}', name) and not any(c.isdigit() for c in name):
            # 纯文字短行（如 "注"）也保留？跳过
            if len(name) <= 2:
                continue
        # 金额错位修复
        price = str(it.get("price") or "").strip()
        amount = str(it.get("amount") or "").strip()
        if price and amount and price != amount:
            # 数字去千分位后比较
            p_n = price.replace(",", "").replace("￥", "").replace("¥", "")
            a_n = amount.replace(",", "").replace("￥", "").replace("¥", "")
            try:
                p_f = float(p_n)
                a_f = float(a_n)
                # amount 是 price 的子串（如 1672.64 vs 672.64）→ 修正
                if a_n in p_n and len(p_n) > len(a_n):
                    it["price"] = price
                    it["amount"] = price
                # 数字完全一样但 amount=0 之类
                elif abs(p_f - a_f) < 0.01:
                    it["price"] = price
                    it["amount"] = price
            except ValueError:
                pass
        # 空金额清理（注意：quantity=0 是合法值，不清；price=0 也不该清，否则前端会显示 0 元单价）
        for k in ("spec", "unit", "amount", "taxRate", "taxAmount"):
            v = it.get(k)
            if v in ("-", "—", "0", "0.00", "0.0"):
                it[k] = ""
        # 去重（key = name+amount+taxAmount）
        key = f"{name}|{it.get('amount','')}|{it.get('taxAmount','')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(_normalize_item(it))
    return out




async def list_unlinked_invoices(
    db: AsyncSession, keyword: str = "", page: int = 1, page_size: int = 20
) -> dict:
    """列出可关联的发票（未关联任何 expense、已核验、未入账）
    - 排除 expenses.invoice_id != NULL 的发票
    - 排除 description 含 [关联发票 INV-xxx] 的费用对应的发票
    - 排除 status=submitted/archived 的发票
    - 仅返回 verifyStatus=verified 的发票
    """
    from app.modules.expense.models import Expense
    from sqlalchemy import func as _func, or_ as _or

    # 1) 收集所有"已被占用"的发票 id
    # 1a) expenses.invoice_id IS NOT NULL
    q_linked = select(Expense.invoice_id).where(Expense.invoice_id.isnot(None))
    linked_ids = set(r for r in (await db.execute(q_linked)).scalars().all() if r)

    # 1b) description 含 [关联发票 INV-xxx] 的（兼容老数据）
    desc_rows = (await db.execute(
        select(Expense.description).where(Expense.description.ilike("%[关联发票 INV-%"))
    )).scalars().all()
    import re as _re
    for d in desc_rows:
        for m in _re.finditer(r"\[关联发票 INV-([^\]]+)\]", d or ""):
            inv_no = m.group(1).strip()
            if not inv_no:
                continue
            inv = (await db.execute(select(Invoice).where(Invoice.invoice_no == inv_no))).scalar_one_or_none()
            if inv:
                linked_ids.add(inv.id)

    # 2) 查未在 linked_ids 里的、verifyStatus=verified、status != submitted/archived
    filters = [
        Invoice.verify_status == "verified",
        Invoice.status.notin_(["submitted", "archived", "rejected"]),
    ]
    if linked_ids:
        filters.append(~Invoice.id.in_(linked_ids))
    q = select(Invoice).where(*filters)
    if keyword:
        kw = f"%{keyword}%"
        q = q.where(_or(Invoice.invoice_no.ilike(kw), Invoice.seller_name.ilike(kw)))
    total = (await db.execute(select(_func.count()).select_from(q.subquery()))).scalar() or 0
    q = q.order_by(Invoice.id.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(q)).scalars().all()
    items = [
        {
            "invoiceId": inv.id,
            "invoiceNo": inv.invoice_no,
            "invoiceType": inv.invoice_type,
            "sellerName": inv.seller_name,
            "totalAmount": float(Decimal(inv.total_amount or 0) / 100),
            "issueDate": inv.issue_date.isoformat() if inv.issue_date else None,
            "status": inv.status,
            "verifyStatus": inv.verify_status,
        }
        for inv in rows
    ]
    return {"list": items, "total": total}
async def get_invoice(db: AsyncSession, invoice_id: int) -> dict:
    inv = (await db.execute(select(Invoice).where(Invoice.id == invoice_id))).scalar_one_or_none()
    if not inv:
        raise NotFoundException(f"发票不存在：{invoice_id}")
    # 关联（合同 / 项目 / 回款）
    rels = (await db.execute(
        select(InvoiceRelation).where(InvoiceRelation.invoice_id == invoice_id)
    )).scalars().all()
    relations = [{"type": r.relation_type, "id": r.relation_id} for r in rels]
    # 上传人：单独查（Invoice 没有 relationship 属性），回退到 JOIN
    uploader_name = None
    if inv.uploader_id:
        u = (await db.execute(select(User).where(User.id == inv.uploader_id))).scalar_one_or_none()
        if u:
            uploader_name = u.name or u.username
    return {
        "invoiceId": inv.id, "code": inv.code,
        "invoiceType": inv.invoice_type, "invoiceCode": inv.invoice_code, "invoiceNo": inv.invoice_no,
        "issueDate": inv.issue_date.isoformat() if inv.issue_date else None,
        "sellerName": inv.seller_name, "sellerTaxNo": inv.seller_tax_no,
        "buyerName": inv.buyer_name, "buyerTaxNo": inv.buyer_tax_no,
        "totalAmount": Decimal(inv.total_amount or 0) / 100,
        "totalAmountCn": inv.total_amount_cn,
        "verifyCode": inv.verify_code or "",
        "remarks": inv.remarks or "",
        "taxRate": float(inv.tax_rate or 0),
        "taxAmount": Decimal(inv.tax_amount or 0) / 100,
        "amountExclTax": Decimal(inv.amount_excl_tax or 0) / 100,
        "confidence": float(inv.confidence or 0) / 100,
        "verifyStatus": inv.verify_status, "verifyAt": inv.verify_at.isoformat() if inv.verify_at else None,
        "verifySource": inv.verify_source,
        "items": inv.items or [],
        "status": inv.status,
        "isLinkedContract": inv.is_linked_contract, "isLinkedProject": inv.is_linked_project,
        "fileUrl": inv.file_url, "previewUrl": inv.file_url, "fileId": inv.file_id, "fileSize": inv.file_size,
        "uploaderId": inv.uploader_id, "uploaderName": uploader_name, "uploadedAt": inv.uploaded_at.isoformat() if inv.uploaded_at else None,
        "createdAt": inv.created_at.isoformat() if inv.created_at else None,
        "updatedAt": inv.updated_at.isoformat() if inv.updated_at else None,
        "relations": relations,
        "items": _clean_items(inv.items or []),
        # 原始 OCR（含火车票扩展字段：fromStation/toStation/trainNo/carriageNo/seatNo/seatClass/buyerIdMasked/eTicketNo/rideDate/rideTime）
        "rawOcr": inv.raw_ocr or {},
        # 启发式归类（前端"费用类型"下拉一键带入）
        "expenseType": _classify_expense_category(inv.seller_name, inv.invoice_type) if inv.seller_name else "",
    }


# ===== 更新（编辑字段 + 关联） =====

async def update_invoice(
    db: AsyncSession, invoice_id: int, fields: dict, expense_info: Optional[dict] = None
) -> dict:
    inv = (await db.execute(select(Invoice).where(Invoice.id == invoice_id))).scalar_one_or_none()
    if not inv:
        raise NotFoundException(f"发票不存在：{invoice_id}")

    field_map = {
        "invoiceType": "invoice_type", "invoiceCode": "invoice_code", "invoiceNo": "invoice_no",
        "issueDate": "issue_date", "sellerName": "seller_name", "sellerTaxNo": "seller_tax_no",
        "buyerName": "buyer_name", "buyerTaxNo": "buyer_tax_no",
        "totalAmount": "total_amount", "taxAmount": "tax_amount", "amountExclTax": "amount_excl_tax",
        "taxRate": "tax_rate",
        "verifyStatus": "verify_status",   # 核验状态: pending/verified/rejected
        "verifyAt": "verify_at",           # 核验时间
        "verifySource": "verify_source",   # 核验来源: manual/auto/system
        "verifyCode": "verify_code",       # 校验码
        "remarks": "remarks",             # 备注
    }
    for k, v in (fields or {}).items():
        attr = field_map.get(k, k)
        # 金额单位转换：元 → 分
        if k in ("totalAmount", "taxAmount", "amountExclTax") and isinstance(v, (int, float, Decimal)):
            v = int(Decimal(str(v)) * 100)
        if k == "taxRate":
            v = Decimal(str(v))
        if k == "issueDate" and isinstance(v, str):
            v = date.fromisoformat(v)
        if k == "verifyAt" and isinstance(v, str):
            # ISO 字符串 → datetime（DB 列是 naive，统一转 UTC 后去掉 tzinfo）
            try:
                v = datetime.fromisoformat(v.replace("Z", "+00:00"))
                if v.tzinfo is not None:
                    v = v.astimezone(timezone.utc).replace(tzinfo=None)
            except ValueError:
                v = datetime.fromisoformat(v)
        setattr(inv, attr, v)

    # 核验通过自动写入核验时间
    if fields and fields.get("verifyStatus") == "verified" and not inv.verify_at:
        inv.verify_at = datetime.utcnow()

    # 关联合同/项目
    if expense_info:
        if expense_info.get("contractId"):
            db.add(InvoiceRelation(invoice_id=inv.id, relation_type="contract", relation_id=int(expense_info["contractId"])))
            inv.is_linked_contract = True
        if expense_info.get("projectId"):
            db.add(InvoiceRelation(invoice_id=inv.id, relation_type="project", relation_id=int(expense_info["projectId"])))
            inv.is_linked_project = True

    # 编辑后从 pending_verify 转 verified
    if inv.status == "pending_verify":
        inv.status = "verified"

    # 核验通过不立即创建费用（避免误判"重复报销"）
    # 改为在 submit_invoice（提交入账）时才创建关联费用占位
    await db.commit()
    return await get_invoice(db, inv.id)


def _classify_expense_category(seller_name: Optional[str], invoice_type: Optional[str] = None) -> str:
    """根据销售方名/发票类型启发式归类。Expense.category 标准值：
    差旅 / 招待 / 办公 / 推广 / 培训 / 其他
    """
    name = (seller_name or "").strip()
    itype = (invoice_type or "").strip()
    # 0. 票种级判定（最优先）
    if "铁路" in itype or "火车" in itype or "航空" in itype or "机票" in itype:
        return "差旅"
    if name in ("中国铁路", "中国国家铁路集团", "12306", "国航", "东航", "南航", "海航") or "铁路" in name or "航空" in name or "12306" in name:
        return "差旅"
    # 关键词 → 类别
    rules: list[tuple[list[str], str]] = [
        (["酒店", "宾馆", "招待所", "客栈", "民宿", "度假村", "客房"], "差旅"),
        (["旅游", "旅行社", "票务", "机票", "航空", "高铁"], "差旅"),
        (["出租", "网约车", "出行", "打车", "滴滴"], "差旅"),
        (["餐饮", "饭店", "小菜园", "餐厅", "食堂", "酒店餐饮", "咖啡", "奶茶", "茶馆", "茶艺", "茶舍", "酒吧", "会所"], "招待"),
        (["印刷", "打印", "图文", "复印"], "办公"),
        (["科技", "网络", "软件", "SaaS", "云服务", "云科技"], "软件服务费"),
        (["办公用品", "文具", "耗材"], "办公"),
        (["培训", "教育", "学校", "学院"], "培训"),
        (["广告", "传媒", "推广", "营销"], "推广"),
    ]
    for kws, cat in rules:
        for kw in kws:
            if kw in name:
                return cat
    # 兜底
    return "其他"


async def _link_invoice_to_expense(db, inv, reason: Optional[str] = None) -> None:
    """核验通过后，与销售费用模块联动：upsert 一条 expenses 记录。
    关联标识写到 description（Expense 模型暂未加 invoice_id 列）。
    重复触发幂等：按 title 查重，不覆盖已审批通过的 status。
    reason: 入账事由（前端弹框输入），追加到 description 后便于审计
    """
    from sqlalchemy import select
    from app.modules.expense.models import Expense
    from datetime import date as _date

    inv_no = inv.invoice_no or inv.code or f"id={inv.id}"
    link_tag = f"[关联发票 INV-{inv_no}]"
    reason_text = (reason or "").strip()
    reason_suffix = f"\n入账事由：{reason_text}" if reason_text else ""
    # title 优先带事由（用户能在销售费用"事由"列一眼看到）
    if reason_text:
        title = f"发票报销·{reason_text}·{inv.seller_name or '未知销售方'}·{inv_no}"
    else:
        title = f"发票报销·{inv.seller_name or '未知销售方'}·{inv_no}"

    existing = (await db.execute(
        select(Expense).where(Expense.title == title).limit(1)
    )).scalar_one_or_none()

    # 启发式归类
    cat = _classify_expense_category(inv.seller_name, inv.invoice_type)
    if existing:
        existing.amount = int(inv.total_amount or 0)
        # 已分类错误（比如老 expense 是"其他"）时按销售方重新归类
        if existing.category in (None, "", "其他") and cat != "其他":
            existing.category = cat
        # 已有关联 expense：总是把入账事由追加到 description，便于审计
        # 同时如果新 title 包含事由前缀，刷新 title 让列表能直接看到事由
        if reason_text:
            if reason_text not in (existing.title or ""):
                existing.title = title
            if (existing.description or "") and not existing.description.endswith(reason_suffix):
                existing.description = (existing.description or "") + reason_suffix
            elif not existing.description:
                existing.description = link_tag + reason_suffix
        elif not (existing.description or "").startswith("[关联发票"):
            existing.description = link_tag + (existing.description or "")
    else:
        exp = Expense(
            code=f"EXP-INV-{inv.id}-{int(datetime.utcnow().timestamp())}",
            category=cat,
            title=title,
            description=link_tag + "由发票识别自动生成（入账即关联）" + reason_suffix,
            amount=int(inv.total_amount or 0),
            currency="CNY",
            expense_date=inv.issue_date or _date.today(),
            applicant_id=inv.uploader_id or 1,
            status="draft",
        )
        db.add(exp)
        await db.flush()  # 拿到 exp.id 才能挂 breakdown
        # 入账时默认带一条费用明细：费用类别 + 销售方 + 发票总额（分）
        from app.modules.expense.models import ExpenseBreakdown
        _cat_zh = {
            "差旅": "差旅费", "招待": "业务招待", "办公": "办公用品",
            "推广": "推广费", "培训": "培训费", "软件服务费": "软件服务费",
            "咨询服务费": "咨询服务费", "其他": "其他费用",
        }
        _label = f"{_cat_zh.get(cat, cat)}·{inv.seller_name or '销售方'}" if cat != '其他' else f"{inv.seller_name or '销售方'}"
        db.add(ExpenseBreakdown(
            expense_id=exp.id,
            label=_label,
            amount=int(inv.total_amount or 0),  # 存分（与 Expense.amount 单位一致）
            remark=f"入账自动生成（发票 {inv.invoice_no or inv.code or inv.id}）",
        ))


# ===== 提交入账 =====
async def submit_invoice(db: AsyncSession, invoice_id: int, reason: Optional[str] = None) -> dict:
    inv = (await db.execute(select(Invoice).where(Invoice.id == invoice_id))).scalar_one_or_none()
    if not inv:
        raise NotFoundException(f"发票不存在：{invoice_id}")
    if inv.status not in ("verified",):
        raise ConflictException(f"只有已核验可入账，当前 {inv.status}")
    inv.status = "submitted"
    # 提交入账时自动创建关联费用占位（用于后续报销审批）
    try:
        await _link_invoice_to_expense(db, inv, reason)
    except Exception as e:
        print(f"[link-expense] invoice_id={inv.id} failed: {e}", flush=True)
    await db.commit()
    return await get_invoice(db, inv.id)


# ===== 重新识别 =====
async def recheck_invoice(db: AsyncSession, invoice_id: int) -> dict:
    inv = (await db.execute(select(Invoice).where(Invoice.id == invoice_id))).scalar_one_or_none()
    if not inv:
        raise NotFoundException(f"发票不存在：{invoice_id}")

    # R18.1: 非标准格式（PDF/HEIC/WEBP）必须先转 JPEG 再 OCR
    # 否则 ocr-service 收到 PDF 会 LoadImageError → 上层回退 mock → 用户看到假数据
    try:
        normalized_url, normalized_name, _ = await image_converter.normalize_to_jpeg(
            file_url=inv.file_url or "",
            file_id=inv.file_id or f"INV-{inv.id}",
            save_callback=_save_file,
        )
        ocr_url = normalized_url
        if normalized_url != (inv.file_url or ""):
            from loguru import logger
            logger.info(f"[recheck OCR 转码] {inv.file_url} → {normalized_name} → {normalized_url}")
    except OCRFailedException as e:
        # 转码失败：直接报错，不回退 mock
        raise OCRFailedException(f"重新识别失败（转码错误）：{e}")

    new_ocr = await ocr_client.recognize(inv.file_id or f"INV-{inv.id}", ocr_url)
    from app.integrations.ocr_client import _cn_capital
    # 不管 OCR 成败，都确保 3 个字段已填（OCR 不返时用兜底逻辑）
    try:
        _amount_yuan = Decimal(inv.total_amount or 0) / Decimal(100)
    except Exception:
        _amount_yuan = Decimal(0)
    if new_ocr.get("status") != "failed":
        flat = _flatten_ocr_response(new_ocr)
        inv.invoice_type = flat["invoiceType"]
        inv.invoice_no = flat["invoiceNo"]
        inv.total_amount = flat["totalAmountCents"]
        inv.tax_amount = flat["taxAmountCents"]
        inv.amount_excl_tax = flat["amountExclTaxCents"]
        inv.tax_rate = Decimal(str(flat["taxRate"]))
        inv.confidence = Decimal(str(flat["confidence"])) * 100
        inv.status = flat["status"]
        inv.items = flat["items"]
        inv.raw_ocr = new_ocr
        inv.total_amount_cn = flat.get("totalAmountCn") or _cn_capital(_amount_yuan)
        inv.verify_code = flat.get("verifyCode") or flat.get("verify_code") or ""
        inv.remarks = flat.get("remarks") or ""
        inv.buyer_name = flat["buyerName"]
        inv.buyer_tax_no = flat["buyerTaxNo"]
        inv.seller_name = flat["sellerName"]
        inv.seller_tax_no = flat["sellerTaxNo"]
        inv.invoice_code = flat["invoiceCode"]
        inv.issue_date = _parse_issue_date(flat["issueDate"])
    else:
        # OCR 失败：用现有数据兜底
        inv.status = "rejected"
        if not inv.total_amount_cn:
            inv.total_amount_cn = _cn_capital(_amount_yuan)
        if not inv.verify_code:
            inv.verify_code = ""  # OCR 没返就留空
    inv.status = inv.status if inv.status != "failed" else "rejected"
    await db.commit()

    # R-fix: 重新识别后，如果已 submit 且存在关联 expense，按新 invoice_type 修正 category
    # 避免老 expense 因发票首次归类错误（比如火车票卖家名不匹配 → '其他'）永远错
    if inv.status in ("submitted", "verified"):
        try:
            from app.modules.expense.models import Expense
            from sqlalchemy import select as _sel
            link_tag = f"[关联发票 INV-{inv.invoice_no or inv.id}]"
            stmt = _sel(Expense).where(Expense.description.contains(link_tag))
            rows = (await db.execute(stmt)).scalars().all()
            if rows:
                new_cat = _classify_expense_category(inv.seller_name, inv.invoice_type)
                for r in rows:
                    if r.category in (None, "", "其他") and new_cat != "其他":
                        r.category = new_cat
                    elif r.category != new_cat and new_cat != "其他":
                        # 同步覆盖：火车票→差旅 即使已不是空也升级
                        r.category = new_cat
                await db.commit()
        except Exception as _e:
            print(f"[recheck-fix-category] invoice_id={inv.id} failed: {_e}", flush=True)

    return await get_invoice(db, inv.id)


# ===== 批量上传 =====

async def create_batch_task(
    db: AsyncSession,
    files: list[dict],  # [{fileId, filename, size, url}]
    template_id: Optional[int],
    uploader_id: int,
) -> dict:
    """创建批量任务 + 写 items + 启动后台处理"""
    batch = InvoiceBatchTask(
        code=_gen_batch_code(),
        template_id=template_id,
        total=len(files),
        uploader_id=uploader_id,
        status="processing",
    )
    db.add(batch)
    await db.flush()

    items = []
    for f in files:
        item = InvoiceBatchItem(
            batch_id=batch.id,
            file_id=f["fileId"],
            filename=f.get("filename", ""),
            file_size=f.get("size"),
            file_url=f.get("url"),
            status="queued",
            progress=0,
        )
        db.add(item)
        items.append({"id": None, "file_id": f["fileId"], "filename": f.get("filename", "")})
    await db.commit()
    await db.refresh(batch)

    # 异步启动后台处理
    asyncio.create_task(_process_batch(batch.id, [f["fileId"] for f in files], uploader_id))

    return {
        "batchId": batch.code,
        "batchInternalId": batch.id,
        "total": batch.total,
        "items": [
            {
                "fileId": f["fileId"],
                "filename": f.get("filename", ""),
                "size": f.get("size"),
                "status": "queued",
            }
            for f in files
        ],
    }


async def _process_batch(batch_id: int, file_ids: list[str], uploader_id: int):
    """后台处理批量任务（调用 OCR + SSE 推送）"""
    from app.core.database import AsyncSessionLocal
    from app.modules.invoice_ocr.models import InvoiceBatchItem as _Item

    async with AsyncSessionLocal() as db:
        # 先把每个 item 标 recognizing
        for fid in file_ids:
            item = (await db.execute(
                select(_Item).where(_Item.batch_id == batch_id, _Item.file_id == fid)
            )).scalar_one_or_none()
            if item:
                item.status = "recognizing"
                item.started_at = datetime.utcnow()
        await db.commit()

        # 逐个 OCR
        success = warning = failed = 0
        for fid in file_ids:
            try:
                item = (await db.execute(
                    select(_Item).where(_Item.batch_id == batch_id, _Item.file_id == fid)
                )).scalar_one_or_none()
                if not item:
                    continue

                ocr = await ocr_client.recognize(fid, item.file_url or "")
                item.progress = 0.5
                await db.commit()
                await publish_batch_progress(
                    code_or_id(batch_id, db),  # placeholder
                    fileId=fid, status="recognizing", progress=0.5,
                )

                if ocr.get("status") == "failed":
                    item.status = "failed"
                    item.error_message = ocr.get("error", "识别失败")
                    item.finished_at = datetime.utcnow()
                    failed += 1
                else:
                    flat = _flatten_ocr_response(ocr)
                    inv = Invoice(
                        code=_gen_invoice_code(),
                        invoice_type=flat["invoiceType"],
                        invoice_code=flat["invoiceCode"],
                        invoice_no=flat["invoiceNo"],
                        issue_date=date.fromisoformat(flat["issueDate"]) if isinstance(flat["issueDate"], str) else flat["issueDate"],
                        seller_name=flat["sellerName"], seller_tax_no=flat["sellerTaxNo"],
                        buyer_name=flat["buyerName"], buyer_tax_no=flat["buyerTaxNo"],
                        total_amount=flat["totalAmountCents"],
                        tax_amount=flat["taxAmountCents"],
                        amount_excl_tax=flat["amountExclTaxCents"],
                        tax_rate=Decimal(str(flat["taxRate"])),
                        confidence=Decimal(str(flat["confidence"])) * 100,
                        status=flat["status"],
                        file_url=item.file_url, file_id=fid,
                        items=flat["items"], raw_ocr=ocr,
                        uploader_id=uploader_id,
                    )
                    db.add(inv)
                    await db.flush()
                    item.invoice_id = inv.id
                    item.status = "success" if flat["status"] == "verified" else "warning"
                    item.progress = 1.0
                    item.finished_at = datetime.utcnow()
                    if flat["status"] == "verified":
                        success += 1
                    else:
                        warning += 1
                await db.commit()

                # SSE 推送
                # 用 batch code 而不是 id（前端订阅的是 code）
                batch_code = (await db.execute(
                    select(InvoiceBatchTask.code).where(InvoiceBatchTask.id == batch_id)
                )).scalar()
                if ocr.get("status") != "failed":
                    flat = _flatten_ocr_response(ocr)
                    inv = Invoice(
                        code=_gen_invoice_code(),
                        invoice_type=flat["invoiceType"],
                        invoice_code=flat["invoiceCode"],
                        invoice_no=flat["invoiceNo"],
                        issue_date=date.fromisoformat(flat["issueDate"]) if isinstance(flat["issueDate"], str) else flat["issueDate"],
                        seller_name=flat["sellerName"], seller_tax_no=flat["sellerTaxNo"],
                        buyer_name=flat["buyerName"], buyer_tax_no=flat["buyerTaxNo"],
                        total_amount=flat["totalAmountCents"],
                        tax_amount=flat["taxAmountCents"],
                        amount_excl_tax=flat["amountExclTaxCents"],
                        tax_rate=Decimal(str(flat["taxRate"])),
                        confidence=Decimal(str(flat["confidence"])) * 100,
                        status=flat["status"],
                        file_url=item.file_url, file_id=fid,
                        items=flat["items"], raw_ocr=ocr,
                        uploader_id=uploader_id,
                    )
                # summary
                await publish_batch_summary(batch_code, {
                    "total": len(file_ids),
                    "uploading": 0, "recognizing": len(file_ids) - success - warning - failed,
                    "success": success, "warning": warning, "failed": failed,
                })
            except Exception as e:
                # 单条失败不阻塞整体
                item = (await db.execute(
                    select(_Item).where(_Item.batch_id == batch_id, _Item.file_id == fid)
                )).scalar_one_or_none()
                if item:
                    item.status = "failed"
                    item.error_message = str(e)[:200]
                    item.finished_at = datetime.utcnow()
                failed += 1
                await db.commit()

        # 汇总
        batch = (await db.execute(
            select(InvoiceBatchTask).where(InvoiceBatchTask.id == batch_id)
        )).scalar_one_or_none()
        if batch:
            batch.success = success
            batch.warning = warning
            batch.failed = failed
            batch.status = "done"
            batch.finished_at = datetime.utcnow()
            await db.commit()
            await publish_batch_completed(
                batch.code, batch.finished_at.strftime("%Y-%m-%d %H:%M:%S")
            )


def code_or_id(batch_id: int, db) -> int:
    """Helper - just return id (SSE channel uses code)"""
    return batch_id


# ===== 批量任务状态查询 =====
async def get_batch_status(db: AsyncSession, batch_id: str) -> dict:
    """按 batch code 查（API.md 用 batchId 字符串）"""
    batch = (await db.execute(
        select(InvoiceBatchTask).where(InvoiceBatchTask.code == batch_id)
    )).scalar_one_or_none()
    if not batch:
        raise NotFoundException(f"批量任务不存在：{batch_id}")
    items = (await db.execute(
        select(InvoiceBatchItem).where(InvoiceBatchItem.batch_id == batch.id)
    )).scalars().all()

    return {
        "batchId": batch.code,
        "summary": {
            "total": batch.total, "uploading": batch.uploading,
            "recognizing": batch.recognizing, "success": batch.success,
            "warning": batch.warning, "failed": batch.failed,
        },
        "items": [
            {
                "fileId": it.file_id, "filename": it.filename,
                "status": it.status, "progress": float(it.progress or 0),
                "invoiceId": it.invoice_id, "error": it.error_message,
            }
            for it in items
        ],
    }


# ===== 批量提交入账 =====
async def submit_batch(db: AsyncSession, invoice_ids: list[int], reason: Optional[str] = None) -> dict:
    """批量提交入账。每条都创建费用占位（与单条入账行为一致）。"""
    rows = (await db.execute(
        select(Invoice).where(Invoice.id.in_(invoice_ids), Invoice.status == "verified")
    )).scalars().all()
    for inv in rows:
        inv.status = "submitted"
        try:
            await _link_invoice_to_expense(db, inv, reason)
        except Exception as e:
            print(f"[link-expense] invoice_id={inv.id} failed: {e}", flush=True)
    await db.commit()
    return {"updated": len(rows), "invoiceIds": [r.id for r in rows]}


# ===== 批量重试失败项 =====
async def retry_batch_items(
    db: AsyncSession, batch_code: str, file_ids: list[str]
) -> dict:
    """重试失败项（重新跑 OCR）"""
    batch = (await db.execute(
        select(InvoiceBatchTask).where(InvoiceBatchTask.code == batch_code)
    )).scalar_one_or_none()
    if not batch:
        raise NotFoundException(f"批量任务不存在：{batch_code}")

    items = (await db.execute(
        select(InvoiceBatchItem).where(
            InvoiceBatchItem.batch_id == batch.id,
            InvoiceBatchItem.file_id.in_(file_ids),
            InvoiceBatchItem.status == "failed",
        )
    )).scalars().all()
    for it in items:
        it.status = "queued"
        it.error_message = None
        it.progress = 0
    await db.commit()

    # 重新触发后台处理
    asyncio.create_task(_process_batch(batch.id, file_ids, batch.uploader_id))
    return {"batchId": batch.code, "queued": len(items)}
