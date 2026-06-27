"""
合同模块服务层
"""
import io
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException, ParamErrorException, ConflictException
from app.core.sse import publish_event
from app.modules.contract.models import Contract, ContractTemplate
from app.modules.contract.schemas import (
    ContractCreate, ContractUpdate, ContractApproveRequest,
)
from app.modules.common.models import Client
from app.modules.project.models import Project
from app.modules.auth.models import User
from app.modules.common.approvals import create_flow, act as act_flow, get_flow, serialize_flow


# 合同类型映射（API.md 字符串 → DB enum）
CONTRACT_TYPE_MAP = {
    "销售合同": "sales", "采购合同": "purchase", "服务合同": "service", "框架协议": "framework",
}
CONTRACT_TYPE_REVERSE = {v: k for k, v in CONTRACT_TYPE_MAP.items()}


def _gen_contract_code() -> str:
    return f"HT-{datetime.now().year}-{uuid.uuid4().hex[:3].upper()}"


# ===== 列表 =====

async def list_contracts(
    db: AsyncSession, page: int = 1, page_size: int = 20,
    keyword: str = "", filters: dict = None,
    current_user = None,  # R11B data_scope 过滤
) -> tuple[list[dict], int]:
    filters = filters or {}
    query = select(Contract)
    # R11B 权限细化：data_scope 过滤（manager_id 关联 user.department_id）
    if current_user is not None:
        from app.core.data_scope import build_data_scope_filter_async
        query = await build_data_scope_filter_async(
            db, query, Contract, current_user,
            owner_field=Contract.manager_id,
            owner_via_user_dept=True,
        )
    if keyword:
        query = query.where(or_(Contract.name.ilike(f"%{keyword}%"), Contract.code.ilike(f"%{keyword}%")))
    if filters.get("type"):
        t = filters["type"]
        db_type = CONTRACT_TYPE_MAP.get(t, t)
        query = query.where(Contract.type == db_type)
    if filters.get("status"):
        query = query.where(Contract.status == filters["status"])
    if filters.get("clientId"):
        query = query.where(Contract.client_id == int(filters["clientId"]))
    # 金额区间（合同金额单位为分）
    if filters.get("amountMin") is not None:
        try: query = query.where(Contract.amount >= int(float(filters["amountMin"]) * 100))
        except: pass
    if filters.get("amountMax") is not None:
        try: query = query.where(Contract.amount <= int(float(filters["amountMax"]) * 100))
        except: pass
    # dateRange
    dr = filters.get("dateRange")
    if dr and isinstance(dr, list) and len(dr) == 2:
        try:
            d1 = date.fromisoformat(dr[0]); d2 = date.fromisoformat(dr[1])
            query = query.where(Contract.sign_date >= d1, Contract.sign_date <= d2)
        except Exception:
            pass

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = query.options(
        selectinload(Contract.client), selectinload(Contract.project), selectinload(Contract.manager),
    ).order_by(Contract.id.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()

    items = []
    for c in rows:
        items.append({
            "contractId": c.id, "code": c.code, "name": c.name, "type": CONTRACT_TYPE_REVERSE.get(c.type, c.type),
            "status": c.status,
            "clientId": c.client_id, "clientName": c.client.name if c.client else None,
            "projectId": c.project_id, "projectName": c.project.name if c.project else None,
            "managerId": c.manager_id, "managerName": c.manager.name if c.manager else None,
            "amount": Decimal(c.amount or 0) / 100,
            "currency": c.currency,
            "signDate": c.sign_date, "effectiveDate": c.effective_date, "expireDate": c.expire_date,
            "createdAt": c.created_at,
        })
    return items, total


# ===== 详情 =====

async def get_contract(db: AsyncSession, contract_id: int) -> dict:
    c = (await db.execute(
        select(Contract)
        .where(Contract.id == contract_id)
        .options(
            selectinload(Contract.client), selectinload(Contract.project),
            selectinload(Contract.manager), selectinload(Contract.creator),
        )
    )).scalar_one_or_none()
    if not c:
        raise NotFoundException(f"合同不存在：{contract_id}")

    # 审批流
    flow = await get_flow(db, "contract", c.id)
    approval_flow = serialize_flow(flow, getattr(flow, "_steps_cache", [])) if flow else None

    # 履约聚合（占位：未来关联发票/回款后真实计算）
    performance = {
        "progress": 0,
        "invoicedAmount": 0,
        "receivedAmount": 0,
        "pendingReceivable": float(Decimal(c.amount or 0) / 100),
    }

    return {
        "contractId": c.id, "code": c.code, "name": c.name, "type": CONTRACT_TYPE_REVERSE.get(c.type, c.type),
        "status": c.status,
        "client": {"clientId": c.client.id, "name": c.client.name, "taxNo": c.client.tax_no,
                   "contactName": c.client.contact_name, "contactPhone": c.client.contact_phone} if c.client else None,
        "projectId": c.project_id, "projectName": c.project.name if c.project else None,
        "managerId": c.manager_id, "managerName": c.manager.name if c.manager else None,
        "amount": Decimal(c.amount or 0) / 100,
        "currency": c.currency,
        "signDate": c.sign_date, "effectiveDate": c.effective_date, "expireDate": c.expire_date,
        "duration": _calc_duration(c.effective_date, c.expire_date),
        "paymentMethod": c.payment_method, "paymentTerm": c.payment_term,
        "summary": c.summary, "terms": c.terms or [],
        "approvalFlow": approval_flow,
        "signatures": {
            "partyA": {"signed": c.party_a_signed, "name": "上海数智信息技术有限公司",
                       "signedAt": c.party_a_signed_at.isoformat() if c.party_a_signed_at else None},
            "partyB": {"signed": c.party_b_signed, "name": c.client.name if c.client else None,
                       "signedAt": c.party_b_signed_at.isoformat() if c.party_b_signed_at else None},
        },
        "attachments": [],
        "performance": performance,
        "createdBy": c.created_by, "createdAt": c.created_at, "updatedAt": c.updated_at,
    }


def _calc_duration(start: Optional[date], end: Optional[date]) -> Optional[str]:
    if not start or not end:
        return None
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if months >= 12 and months % 12 == 0:
        return f"{months // 12} 年"
    return f"{months} 个月"


# ===== 创建 =====

async def create_contract(db: AsyncSession, req: ContractCreate, creator_id: int) -> dict:
    db_type = CONTRACT_TYPE_MAP.get(req.type, req.type)
    if db_type not in ("sales", "purchase", "service", "framework"):
        raise ParamErrorException(f"合同类型无效：{req.type}")

    c = Contract(
        code=_gen_contract_code(),
        name=req.name, type=db_type,
        client_id=req.clientId, project_id=req.projectId, manager_id=req.managerId,
        # 前端传"元"，DB 存"分"（*100）
        amount=req.amount * 100, currency=req.currency,
        sign_date=req.signDate, effective_date=req.effectiveDate, expire_date=req.expireDate,
        payment_method=req.paymentMethod, payment_term=req.paymentTerm,
        summary=req.summary, status="draft", created_by=creator_id,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return await get_contract(db, c.id)


# ===== 更新 =====

async def update_contract(db: AsyncSession, contract_id: int, req: ContractUpdate) -> dict:
    c = (await db.execute(select(Contract).where(Contract.id == contract_id))).scalar_one_or_none()
    if not c:
        raise NotFoundException(f"合同不存在：{contract_id}")
    if c.status not in ("draft",):
        raise ConflictException(f"当前状态（{c.status}）不可编辑")

    data = req.model_dump(exclude_unset=True)
    field_map = {
        "clientId": "client_id", "projectId": "project_id", "managerId": "manager_id",
        "signDate": "sign_date", "effectiveDate": "effective_date", "expireDate": "expire_date",
        "paymentMethod": "payment_method", "paymentTerm": "payment_term",
    }
    for k, v in data.items():
        if k == "type":
            setattr(c, "type", CONTRACT_TYPE_MAP.get(v, v))
        elif k == "amount":
            # 与 create_contract 保持一致：API 入参是元，DB 存分（×100）
            c.amount = v * 100
        else:
            setattr(c, field_map.get(k, k), v)
    await db.commit()
    await db.refresh(c)
    return await get_contract(db, c.id)


# ===== 删除 =====

async def delete_contract(db: AsyncSession, contract_id: int):
    c = (await db.execute(select(Contract).where(Contract.id == contract_id))).scalar_one_or_none()
    if not c:
        raise NotFoundException(f"合同不存在：{contract_id}")
    # 业务护：审批中 / 已签订 不可删
    if c.status in ("approving", "signed", "approved"):
        raise ConflictException(
            f"合同状态为「{c.status}」不允许删除，请先处理（撤销审批 / 解除签订）后再试"
        )
    await db.delete(c)
    await db.commit()


async def batch_delete_contracts(db: AsyncSession, contract_ids: list[int]) -> dict:
    """批量删除合同。仅 draft / expired / archived / terminated 状态可删；
    approving / signed / approved 状态跳过并在 skipped 中返回原因。"""
    if not contract_ids:
        return {"deleted": 0, "skipped": [], "deletedIds": []}
    rows = (await db.execute(select(Contract).where(Contract.id.in_(contract_ids)))).scalars().all()
    forbidden = {"approving", "signed", "approved"}
    status_label = {
        "draft": "草稿", "approving": "审批中", "approved": "已审批",
        "signed": "已签订", "executed": "执行中", "expired": "已到期",
        "archived": "已归档", "terminated": "已终止",
    }
    deletable = []
    skipped = []
    for c in rows:
        if c.status in forbidden:
            skipped.append({
                "id": c.id, "code": c.code,
                "reason": f"状态为「{status_label.get(c.status, c.status)}」不允许删除",
            })
        else:
            deletable.append(c)
    for c in deletable:
        await db.delete(c)
    await db.commit()
    return {
        "deleted": len(deletable),
        "skipped": skipped,
        "deletedIds": [c.id for c in deletable],
    }


# ===== 提交审批（draft → approving） =====
async def submit_for_approval(db: AsyncSession, contract_id: int, user_id: int) -> dict:
    c = (await db.execute(select(Contract).where(Contract.id == contract_id))).scalar_one_or_none()
    if not c:
        raise NotFoundException(f"合同不存在：{contract_id}")
    if c.status != "draft":
        raise ConflictException(f"只有 draft 状态可提交审批，当前 {c.status}")

    # 创建审批流（4 步：提交→直属上级→法务/财务审核→总经理审批(若≥5万)）
    rules = ["submitter", "direct_leader", "finance"]
    if c.amount >= 5000000:  # 5 万元 = 500000 分
        rules.append("gm_if_over_5000")
    await create_flow(db, "contract", c.id, rules, user_id, c.amount)

    c.status = "approving"
    await db.commit()
    return await get_contract(db, c.id)


# ===== 审批动作 =====
async def approve_contract(
    db: AsyncSession, req: ContractApproveRequest, operator_id: int
) -> dict:
    c = (await db.execute(select(Contract).where(Contract.id == req.contractId))).scalar_one_or_none()
    if not c:
        raise NotFoundException(f"合同不存在：{req.contractId}")
    flow = await get_flow(db, "contract", c.id)
    if not flow:
        raise NotFoundException("未找到审批流")
    await act_flow(db, flow.id, req.action, operator_id, req.comment, req.transferTo)

    # 状态机推进（BACKEND.md §5.2）
    await db.refresh(flow)
    if flow.status == "approved":
        c.status = "approved"
    elif flow.status == "rejected":
        c.status = "draft"
    await db.commit()
    return await get_contract(db, c.id)


# ===== 统计 =====
async def get_stats(db: AsyncSession) -> dict:
    today = date.today()
    soon = today + timedelta(days=30)
    total = (await db.execute(select(func.count()).select_from(Contract))).scalar() or 0
    executed = (await db.execute(
        select(func.count()).where(Contract.status.in_(["signed", "executed"]))
    )).scalar() or 0
    total_amt = (await db.execute(
        select(func.coalesce(func.sum(Contract.amount), 0))
    )).scalar() or 0
    pending = (await db.execute(
        select(func.count()).where(Contract.status == "approving")
    )).scalar() or 0
    expiring = (await db.execute(
        select(func.count()).where(
            Contract.status == "executed",
            Contract.expire_date != None,
            Contract.expire_date <= soon,
            Contract.expire_date >= today,
        )
    )).scalar() or 0
    return {
        "total": total, "executed": executed,
        "totalAmount": Decimal(total_amt) / 100,
        "pendingApproval": pending, "expiringSoon": expiring,
    }


# ===== 合同模板列表 =====
async def list_contract_templates(db: AsyncSession) -> list[dict]:
    rows = (await db.execute(
        select(ContractTemplate).where(ContractTemplate.is_active == True)
        .order_by(ContractTemplate.id.asc())
    )).scalars().all()
    return [
        {"id": t.id, "name": t.name, "type": CONTRACT_TYPE_REVERSE.get(t.type, t.type)}
        for t in rows
    ]


# ===== 催办 =====
async def urge_contract(
    db: AsyncSession,
    contract_id: int,
    operator_id: int,
    operator_name: str,
    message: Optional[str] = None,
    target_user_ids: Optional[list[int]] = None,
) -> dict:
    """合同催办：向指定审批人发 Notification + SSE 通知。"""
    from app.modules.common.models import Notification, ApprovalFlow, ApprovalStep

    c = (await db.execute(select(Contract).where(Contract.id == contract_id))).scalar_one_or_none()
    if not c:
        raise NotFoundException(f"合同不存在：{contract_id}")
    if c.status != "approving":
        raise ConflictException(f"只有「审批中」状态可催办，当前 {c.status}")

    # 解析催办对象
    if not target_user_ids:
        # 默认取当前审批流 current step 的 approver
        flow = (await db.execute(
            select(ApprovalFlow)
            .where(ApprovalFlow.business_type == "contract", ApprovalFlow.business_id == c.id)
            .order_by(ApprovalFlow.id.desc())
        )).scalar_one_or_none()
        if flow and flow.status == "in_progress":
            step = (await db.execute(
                select(ApprovalStep)
                .where(ApprovalStep.flow_id == flow.id, ApprovalStep.status == "current")
            )).scalar_one_or_none()
            if step and step.approver_id:
                target_user_ids = [step.approver_id]
        if not target_user_ids:
            # 最后兜底：合同负责人
            target_user_ids = [c.manager_id] if c.manager_id else []
    if not target_user_ids:
        raise ParamErrorException("未找到可催办的审批人")

    msg = (message or "").strip() or f"请尽快审批合同 {c.code} {c.name}"
    notif_title = f"【催办】合同 {c.code} 等待审批"
    notif_link = f"/contract/{c.id}"

    notified = []
    for uid in target_user_ids:
        n = Notification(
            user_id=uid,
            type="mention",
            title=notif_title,
            content=f"{operator_name} 催办：{msg}",
            link=notif_link,
        )
        db.add(n)
        notified.append(uid)
    await db.commit()

    # SSE 通知（dashboard / 通知页能即时收到）
    await publish_event("sse:dashboard", "contract.urge", {
        "contractId": c.id, "code": c.code, "name": c.name,
        "operator": operator_name, "message": msg, "targets": notified,
    })
    for uid in notified:
        await publish_event(f"sse:user:{uid}", "notification", {
            "type": "mention", "title": notif_title, "link": notif_link,
        })

    return {
        "contractId": c.id,
        "notifiedUserIds": notified,
        "message": msg,
    }


# ===== 下载（PDF 摘要） =====
def _build_contract_pdf(c: Contract) -> bytes:
    """生成合同摘要 PDF（单页 A4）。"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfgen import canvas
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    # 注册中文字体（重复注册是幂等的）
    try:
        pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    except Exception:
        pass

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
        title=f"合同 {c.code}",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title", parent=styles["Title"], fontName="STSong-Light",
        fontSize=20, alignment=1, spaceAfter=14,
    )
    h2 = ParagraphStyle(
        "H2", parent=styles["Heading2"], fontName="STSong-Light",
        fontSize=13, spaceBefore=12, spaceAfter=6, textColor=colors.HexColor("#4F6BFF"),
    )
    body = ParagraphStyle(
        "Body", parent=styles["BodyText"], fontName="STSong-Light",
        fontSize=10, leading=15,
    )
    small = ParagraphStyle(
        "Small", parent=body, fontSize=9, textColor=colors.grey,
    )

    def _v(x):
        return "—" if x is None or x == "" else str(x)

    amount_yuan = f"¥ {Decimal(c.amount or 0) / 100:,.2f}" if c.amount else "—"
    type_label = CONTRACT_TYPE_REVERSE.get(c.type, c.type)
    status_label_map = {
        "draft": "草稿", "approving": "审批中", "approved": "已审批",
        "signed": "已签订", "executed": "执行中", "expired": "已到期",
        "archived": "已归档", "terminated": "已终止",
    }

    story = []
    story.append(Paragraph("合 同 摘 要", title_style))
    story.append(Paragraph(
        f"合同编号：<b>{_v(c.code)}</b>　|　类型：{_v(type_label)}　|　状态：{status_label_map.get(c.status, c.status)}",
        small,
    ))
    story.append(Spacer(1, 6 * mm))

    # 基本信息表
    rows = [
        ["合同名称", _v(c.name), "合同编号", _v(c.code)],
        ["客户", _v(c.client.name if c.client else None), "负责人", _v(c.manager.name if c.manager else None)],
        ["合同金额", amount_yuan, "币种", _v(c.currency or "CNY")],
        ["签订日期", _v(c.sign_date), "生效日期", _v(c.effective_date)],
        ["到期日期", _v(c.expire_date), "付款方式", _v(c.payment_method)],
    ]
    tbl = Table(rows, colWidths=[28 * mm, 60 * mm, 28 * mm, 50 * mm])
    tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F4F6FB")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F4F6FB")),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#6B7280")),
        ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor("#6B7280")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tbl)

    # 合同摘要
    story.append(Paragraph("合同摘要", h2))
    story.append(Paragraph(_v(c.summary) or "（无）", body))

    # 条款
    story.append(Paragraph("主要条款", h2))
    terms = c.terms or []
    if terms:
        for t in terms:
            title = t.get("title", "—") if isinstance(t, dict) else "—"
            content = t.get("content", "") if isinstance(t, dict) else str(t)
            story.append(Paragraph(f"• <b>{_v(title)}</b>", body))
            story.append(Paragraph(_v(content), body))
            story.append(Spacer(1, 2 * mm))
    else:
        story.append(Paragraph("（无）", body))

    # 签署
    story.append(Paragraph("签署情况", h2))
    sign_rows = [
        ["甲方（数智信息）", "已签署" if c.party_a_signed else "未签署",
         c.party_a_signed_at.strftime("%Y-%m-%d %H:%M") if c.party_a_signed_at else "—"],
        ["乙方（客户）", "已签署" if c.party_b_signed else "未签署",
         c.party_b_signed_at.strftime("%Y-%m-%d %H:%M") if c.party_b_signed_at else "—"],
    ]
    sign_tbl = Table(sign_rows, colWidths=[60 * mm, 30 * mm, 70 * mm])
    sign_tbl.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#E5E7EB")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(sign_tbl)

    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(
        f"本摘要由数智化管理系统自动生成 · {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        small,
    ))

    doc.build(story)
    return buf.getvalue()


async def download_contract(db: AsyncSession, contract_id: int) -> tuple[bytes, str, str]:
    """返回 (pdf_bytes, filename, content_type)"""
    from sqlalchemy.orm import selectinload

    c = (await db.execute(
        select(Contract)
        .where(Contract.id == contract_id)
        .options(
            selectinload(Contract.client), selectinload(Contract.manager),
        )
    )).scalar_one_or_none()
    if not c:
        raise NotFoundException(f"合同不存在：{contract_id}")
    pdf = _build_contract_pdf(c)
    fname = f"合同_{c.code}_{datetime.now().strftime('%Y%m%d')}.pdf"
    return pdf, fname, "application/pdf"
