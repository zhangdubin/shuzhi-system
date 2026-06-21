"""
发票查验服务（诺诺发票云 mock）
"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, or_, select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException, ParamErrorException
from app.modules.invoice_ocr.models import Invoice, InvoiceVerifyRecord
from app.modules.auth.models import User
from app.integrations import nuonuo


def _gen_verify_code() -> str:
    return f"VR-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:3].upper()}"


# ===== 单张验真 =====
async def verify_single(
    db: AsyncSession,
    invoice_code: str,
    invoice_no: str,
    issue_date: str,
    total_amount_yuan: float,
    verify_code: Optional[str] = None,
    operator_id: Optional[int] = None,
) -> dict:
    """调用诺诺验真 + 写记录"""
    result = await nuonuo.verify(invoice_code, invoice_no, issue_date, total_amount_yuan, verify_code)

    # 真伪判定由 nuonuo.verify() 完成（生产调国税；mock 走数据库驱动判断）：
    #   pass       = 国税有数据，本系统未报销
    #   risk       = 同号但金额不一致
    #   repeat     = 同号且已生成 expense 报销记录
    #   not_found  = 字段格式不合法 / 模拟国税查无此票
    # 服务层不覆盖 result，让国税说了算。

    rec = InvoiceVerifyRecord(
        code=_gen_verify_code(),
        invoice_id=invoice_id,  # 从识别记录选择的会带上
        invoice_code=invoice_code, invoice_no=invoice_no,
        issue_date=date.fromisoformat(issue_date) if issue_date else None,
        total_amount=int(Decimal(str(total_amount_yuan)) * 100),
        result=result["result"],
        source=result["source"],
        risk_reason=result.get("riskReason"),
        elapsed_ms=result["elapsed"],
        operator_id=operator_id,
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)

    # 回写真实 verifyId
    result["verifyId"] = rec.code
    return result


# ===== 批量验真 =====
async def verify_batch(
    db: AsyncSession,
    invoices: list[dict],
    operator_id: Optional[int] = None,
) -> dict:
    """批量验真（一次最多 50）"""
    if len(invoices) > 50:
        raise ParamErrorException("批量验真一次最多 50 张")

    results = []
    pass_count = risk_count = 0
    for inv in invoices:
        r = await verify_single(
            db,
            inv.get("invoiceCode", ""),
            inv.get("invoiceNo", ""),
            inv.get("issueDate", ""),
            inv.get("totalAmount", 0.0),
            inv.get("verifyCode"),
            operator_id,
            inv.get("invoiceId"),
        )
        results.append(r)
        if r["result"] == "pass":
            pass_count += 1
        else:
            risk_count += 1

    return {
        "batchId": f"VR-BATCH-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "total": len(results),
        "summary": {"pass": pass_count, "risk": risk_count},
        "items": results,
    }


# ===== 查验记录列表 =====
async def list_verify_records(
    db: AsyncSession, page: int = 1, page_size: int = 20, filters: dict = None
) -> tuple[list[dict], int]:
    filters = filters or {}
    query = select(InvoiceVerifyRecord)
    if filters.get("result") and filters["result"] != "all":
        query = query.where(InvoiceVerifyRecord.result == filters["result"])
    if filters.get("dateRange"):
        dr = filters["dateRange"]
        if isinstance(dr, list) and len(dr) == 2:
            try:
                d1 = date.fromisoformat(dr[0]); d2 = date.fromisoformat(dr[1])
                query = query.where(InvoiceVerifyRecord.verified_at >= datetime.combine(d1, datetime.min.time()),
                                    InvoiceVerifyRecord.verified_at <= datetime.combine(d2, datetime.max.time()))
            except Exception:
                pass

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    # 用 outerjoin 把关联发票的销售方/购买方带出来（缺失时为 None）
    query = (
        query.outerjoin(Invoice, Invoice.id == InvoiceVerifyRecord.invoice_id)
             .add_columns(
                 Invoice.seller_name.label("seller_name"),
                 Invoice.buyer_name.label("buyer_name"),
                 Invoice.seller_tax_no.label("seller_tax_no"),
             )
             .order_by(InvoiceVerifyRecord.id.desc())
             .offset((page - 1) * page_size)
             .limit(page_size)
    )
    rows = (await db.execute(query)).all()

    items = []
    # 收集本批 invoice_no 一次查重，避免 N+1
    invoice_nos = list({r.invoice_no for r, *_ in rows if r.invoice_no})
    dup_map: dict[str, dict] = {}
    if invoice_nos:
        # 1) 状态维度的"已识别"（verified / submitted / approved / linked）
        dup_q = select(Invoice).where(
            Invoice.invoice_no.in_(invoice_nos),
            Invoice.status.in_(["verified", "submitted", "linked", "approved"]),
        )
        for inv in (await db.execute(dup_q)).scalars().all():
            # 同号可能多张：只取第一张作为代表
            dup_map.setdefault(inv.invoice_no, {
                "duplicate": True,
                "matchedCode": inv.code,
                "matchedStatus": inv.status,
                "matchedSellerName": inv.seller_name,
            })
        # 2) 报销维度的"已识别"（即使 invoice 状态不是 approved/rejected，只要关联了 expense）
        from app.modules.invoice_ocr.models import InvoiceRelation
        from app.modules.expense.models import Expense
        rel_q = (
            select(InvoiceRelation, Invoice, Expense)
            .join(Invoice, Invoice.id == InvoiceRelation.invoice_id)
            .join(Expense, Expense.id == InvoiceRelation.relation_id)
            .where(
                InvoiceRelation.relation_type == "expense",
                Invoice.invoice_no.in_(invoice_nos),
            )
        )
        for rel, inv, exp in (await db.execute(rel_q)).all():
            if inv.invoice_no in dup_map:
                continue
            dup_map.setdefault(inv.invoice_no, {
                "duplicate": True,
                "matchedCode": exp.code or inv.code,
                "matchedStatus": f"关联费用 {exp.status}",
                "matchedSellerName": inv.seller_name,
            })

    for r, seller_name, buyer_name, seller_tax_no in rows:
        dup = dup_map.get(r.invoice_no)
        items.append({
            "verifyId": r.code,
            "invoiceCode": r.invoice_code,
            "invoiceNo": r.invoice_no,
            "issueDate": r.issue_date.isoformat() if r.issue_date else None,
            "totalAmount": Decimal(r.total_amount or 0) / 100,
            "result": r.result,
            "source": r.source,
            "riskReason": r.risk_reason,
            "elapsed": r.elapsed_ms,
            "verifiedAt": r.verified_at.isoformat() if r.verified_at else None,
            "sellerName": seller_name or "",
            "buyerName": buyer_name or "",
            "sellerTaxNo": seller_tax_no or "",
            "internalDuplicate": dup,
        })
    return items, total


# ===== 下载凭证（PDF 生成）=====
async def get_certificate(db: AsyncSession, verify_id: str) -> dict:
    """下载查验凭证（PDF）—— 动态生成，包含发票信息+查验结果+二维码+水印"""
    rec = (await db.execute(
        select(InvoiceVerifyRecord).where(InvoiceVerifyRecord.code == verify_id)
    )).scalar_one_or_none()
    if not rec:
        raise NotFoundException(f"查验记录不存在：{verify_id}")

    # 关联发票（销售方等）
    inv = None
    if rec.invoice_no:
        inv = (await db.execute(
            select(Invoice).where(Invoice.invoice_no == rec.invoice_no)
        )).scalar_one_or_none()

    # 生成 PDF（同步在 async 里跑，文件不大；生产可放 BackgroundTasks）
    from app.modules.invoice_verify.cert_generator import generate_certificate_pdf
    pdf_path = await generate_certificate_pdf(rec, inv)
    return {
        "verifyId": rec.code,
        "certificateUrl": f"/static/certificates/{rec.code}.pdf",
        "message": "查验凭证已生成",
    }


# ===== 标记风险 =====
async def mark_risk(
    db: AsyncSession,
    verify_id: str,
    action: str,  # mark/isolate/report
    comment: Optional[str] = None,
    operator_id: Optional[int] = None,
) -> dict:
    """标记风险发票（暂写 audit_log，无专门表）"""
    from app.modules.auth.models import AuditLog
    rec = (await db.execute(
        select(InvoiceVerifyRecord).where(InvoiceVerifyRecord.code == verify_id)
    )).scalar_one_or_none()
    if not rec:
        raise NotFoundException(f"查验记录不存在：{verify_id}")

    log = AuditLog(
        operator_id=operator_id,
        action=f"verify_{action}",
        resource_type="invoice_verify",
        resource_id=rec.id,
        body=comment or "",
    )
    db.add(log)
    await db.commit()
    return {"verifyId": rec.code, "action": action, "marked": True}
