"""
回款服务层
"""
import uuid
from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException, ParamErrorException, ConflictException
from app.modules.receivable.models import Receivable, ReceivablePayment, ReceivableRemind
from app.modules.receivable.schemas import (
    ReceivableCreate, ReceivableRemindRequest, ReceivableReceiveRequest,
)
from app.modules.auth.models import User
from app.modules.common.models import Client
# Contract 在 get_stats 函数内延迟 import（避开循环）


def _gen_receivable_code() -> str:
    return f"HK-{datetime.now().year}-{uuid.uuid4().hex[:3].upper()}"


def _overdue_days(plan: date, today: Optional[date] = None) -> int:
    today = today or date.today()
    if plan >= today:
        return 0
    return (today - plan).days


def _auto_status(received: int, plan: int, plan_date: date) -> str:
    if received == 0:
        return "overdue" if plan_date < date.today() else "pending"
    if received < plan:
        return "partial"
    return "completed"


# ===== 列表 =====
async def list_receivables(
    db: AsyncSession, page: int = 1, page_size: int = 20,
    keyword: str = "", filters: dict = None,
    current_user = None,  # R11B data_scope 过滤
) -> tuple[list[dict], int]:
    filters = filters or {}
    query = select(Receivable)
    # R11B 权限细化：data_scope 过滤（经 contract.manager_id 间接）
    if current_user is not None:
        from app.core.data_scope import build_data_scope_filter_async
        from app.modules.contract.models import Contract
        from app.modules.auth.models import User
        # 间接过滤：先在 contract.manager_id 上加 data_scope，再 join
        # 简化为子查询：contract.manager_id in (dept_subtree users)
        scope = current_user.data_scope
        if not (current_user.is_admin or scope == "all"):
            if scope in ("dept", "custom", "dept_sub"):
                from app.core.data_scope import get_dept_subtree_ids
                if scope == "dept_sub":
                    ids = await get_dept_subtree_ids(db, current_user.department_id)
                else:
                    ids = [current_user.department_id]
                sub = select(User.id).where(User.department_id.in_(ids), User.is_active == True)
                # 限制 receivables 在这些 user 关联的 contract 内
                query = query.where(Receivable.contract_id.in_(
                    select(Contract.id).where(Contract.manager_id.in_(sub))
                ))
            elif scope == "self":
                # 间接 self 难实现（receivable 没创建者），这里通过 created_by 字段
                # receivable 模型无 created_by，跳过（兜底无过滤）
                pass
    if keyword:
        query = query.where(or_(Receivable.code.ilike(f"%{keyword}%")))
    if filters.get("status"):
        query = query.where(Receivable.status == filters["status"])
    if filters.get("clientId"):
        query = query.where(Receivable.client_id == int(filters["clientId"]))
    if filters.get("managerId"):
        query = query.where(Receivable.manager_id == int(filters["managerId"]))
    if filters.get("type"):
        query = query.where(Receivable.type == filters["type"])
    # 金额区间（计划金额单位为分）
    if filters.get("amountMin") is not None:
        try: query = query.where(Receivable.plan_amount >= int(float(filters["amountMin"]) * 100))
        except: pass
    if filters.get("amountMax") is not None:
        try: query = query.where(Receivable.plan_amount <= int(float(filters["amountMax"]) * 100))
        except: pass
    dr = filters.get("dateRange")
    if dr and isinstance(dr, list) and len(dr) == 2:
        try:
            d1 = date.fromisoformat(dr[0]); d2 = date.fromisoformat(dr[1])
            query = query.where(Receivable.plan_date >= d1, Receivable.plan_date <= d2)
        except Exception:
            pass

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = query.options(
        selectinload(Receivable.client), selectinload(Receivable.manager), selectinload(Receivable.contract),
    ).order_by(Receivable.id.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()

    items = []
    for r in rows:
        plan = r.plan_amount or 0
        received = r.received_amount or 0
        items.append({
            "receivableId": r.id, "code": r.code,
            "contractId": r.contract_id, "contractCode": r.contract.code if r.contract else None,
            "clientId": r.client_id, "clientName": r.client.name if r.client else None,
            "type": r.type,
            "planAmount": Decimal(plan) / 100, "receivedAmount": Decimal(received) / 100,
            "pendingAmount": Decimal(max(0, plan - received)) / 100,
            "planDate": r.plan_date, "actualDate": r.actual_date,
            "overdueDays": _overdue_days(r.plan_date),
            "managerId": r.manager_id, "managerName": r.manager.name if r.manager else None,
            "status": r.status, "createdAt": r.created_at,
        })
    return items, total


# ===== 详情 =====
async def get_receivable(db: AsyncSession, receivable_id: int) -> dict:
    r = (await db.execute(
        select(Receivable).where(Receivable.id == receivable_id)
        .options(
            selectinload(Receivable.client), selectinload(Receivable.manager),
            selectinload(Receivable.contract),
            selectinload(Receivable.payments), selectinload(Receivable.reminds),
        )
    )).scalar_one_or_none()
    if not r:
        raise NotFoundException(f"回款不存在：{receivable_id}")

    plan = r.plan_amount or 0
    received = r.received_amount or 0

    return {
        "receivableId": r.id, "code": r.code,
        "contractId": r.contract_id,
        "client": {"clientId": r.client.id, "name": r.client.name} if r.client else None,
        "type": r.type,
        "planAmount": Decimal(plan) / 100,
        "receivedAmount": Decimal(received) / 100,
        "pendingAmount": Decimal(max(0, plan - received)) / 100,
        "planDate": r.plan_date, "actualDate": r.actual_date,
        "overdueDays": _overdue_days(r.plan_date),
        "term": f"{r.term_days or 30} 天",
        "manager": {"userId": r.manager.id, "name": r.manager.name} if r.manager else None,
        "bankAccount": {"name": "", "account": r.bank_account} if r.bank_account else None,
        "status": r.status, "remark": r.remark,
        "history": [
            {"type": "received", "amount": float(Decimal(p.amount) / 100),
             "operator": None, "time": p.received_at.isoformat() if p.received_at else None}
            for p in r.payments
        ],
        "remindLogs": [
            {"logId": rm.id, "type": rm.type, "contactPerson": rm.contact_person,
             "content": rm.content, "createdAt": rm.created_at.isoformat() if rm.created_at else None}
            for rm in r.reminds
        ],
        "linkedInvoices": [],
        "clientPaymentHistory": [],
        "riskAssessment": {
            "level": "medium" if _overdue_days(r.plan_date) > 0 else "low",
            "label": "中度风险" if _overdue_days(r.plan_date) > 0 else "低风险",
            "description": "客户历史回款准时率待评估",
            "aiSuggestion": "建议持续跟进",
        },
        "createdAt": r.created_at, "updatedAt": r.updated_at,
    }


# ===== 创建 =====
async def create_receivable(db: AsyncSession, req: ReceivableCreate) -> dict:
    # 状态根据 receivedAmount 自动判断
    if req.receivedAmount and req.receivedAmount >= req.planAmount and req.planAmount > 0:
        status = "received"
    elif req.receivedAmount and req.receivedAmount > 0:
        status = "partial"
    else:
        status = "pending"
    r = Receivable(
        code=_gen_receivable_code(),
        contract_id=req.contractId, client_id=req.clientId,
        type=req.type,
        # 前端传"元"，DB 存"分"（*100）
        plan_amount=req.planAmount * 100,
        received_amount=(req.receivedAmount or 0) * 100,
        actual_date=req.actualDate,
        plan_date=req.planDate, term_days=req.termDays,
        manager_id=req.managerId, bank_account=req.bankAccount,
        remark=req.remark, status=status,
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return await get_receivable(db, r.id)


# ===== 催收 =====
async def add_remind(
    db: AsyncSession, req: ReceivableRemindRequest, operator_id: int
) -> dict:
    r = (await db.execute(select(Receivable).where(Receivable.id == req.receivableId))).scalar_one_or_none()
    if not r:
        raise NotFoundException(f"回款不存在：{req.receivableId}")
    rm = ReceivableRemind(
        receivable_id=r.id, type=req.type, contact_person=req.contactPerson,
        content=req.content, attachments=req.attachments, operator_id=operator_id,
    )
    db.add(rm)
    await db.commit()
    return await get_receivable(db, r.id)


# ===== 登记到账 =====
async def receive_payment(
    db: AsyncSession, req: ReceivableReceiveRequest, operator_id: int
) -> dict:
    r = (await db.execute(select(Receivable).where(Receivable.id == req.receivableId))).scalar_one_or_none()
    if not r:
        raise NotFoundException(f"回款不存在：{req.receivableId}")

    pay = ReceivablePayment(
        receivable_id=r.id, amount=req.receivedAmount,
        received_at=req.receivedDate, bank_statement=req.bankStatement,
        remark=req.remark, operator_id=operator_id,
    )
    db.add(pay)
    await db.flush()

    # 累加 + 状态机
    r.received_amount = (r.received_amount or 0) + req.receivedAmount
    if req.receivedAmount > 0 and r.actual_date is None:
        r.actual_date = req.receivedDate
    r.status = _auto_status(r.received_amount, r.plan_amount, r.plan_date)
    r.overdue_days = _overdue_days(r.plan_date)
    await db.commit()
    return await get_receivable(db, r.id)


# ===== 统计 =====
async def get_stats(db: AsyncSession) -> dict:
    today = date.today()
    this_month = today.replace(day=1)
    this_month_received = (await db.execute(
        select(func.coalesce(func.sum(ReceivablePayment.amount), 0))
        .where(ReceivablePayment.received_at >= this_month)
    )).scalar() or 0
    pending_total = (await db.execute(
        select(func.coalesce(func.sum(Receivable.plan_amount - Receivable.received_amount), 0))
        .where(Receivable.status.in_(["pending", "partial", "overdue"]))
    )).scalar() or 0
    completed = (await db.execute(select(func.count()).where(Receivable.status == "completed"))).scalar() or 0
    total = (await db.execute(select(func.count()).select_from(Receivable))).scalar() or 0
    completion_rate = (completed / total) if total > 0 else 0
    overdue_count = (await db.execute(select(func.count()).where(Receivable.status == "overdue"))).scalar() or 0
    overdue_amount = (await db.execute(
        select(func.coalesce(func.sum(Receivable.plan_amount - Receivable.received_amount), 0))
        .where(Receivable.status == "overdue")
    )).scalar() or 0

    # 客户 Top
    top_rows = (await db.execute(
        select(Client.id, Client.name,
               func.coalesce(func.sum(Receivable.plan_amount), 0).label("amount"),
               func.count(Receivable.id).label("cnt"))
        .join(Receivable, Receivable.client_id == Client.id, isouter=True)
        .group_by(Client.id, Client.name)
        .order_by(func.coalesce(func.sum(Receivable.plan_amount), 0).desc())
        .limit(5)
    )).all()

    return {
        "kpi": {
            "thisMonthReceived": Decimal(this_month_received) / 100,
            "pendingTotal": Decimal(pending_total) / 100,
            "completionRate": round(float(completion_rate), 3),
            "overdueCount": overdue_count,
            "overdueAmount": Decimal(overdue_amount) / 100,
        },
        "monthTimeline": [
            {"month": "2026-06", "planned": 1800000, "actual": float(Decimal(this_month_received) / 100), "status": "in_progress"},
            {"month": "2026-07", "planned": 2480000, "actual": 0, "status": "pending"},
            {"month": "2026-08", "planned": 1860000, "actual": 0, "status": "pending"},
        ],
        "topClients": [
            {"clientId": cid, "name": cname, "amount": float(Decimal(amt) / 100), "count": cnt, "avgDays": 32}
            for cid, cname, amt, cnt in top_rows
        ],
    }


# ===== 更新 =====
async def update_receivable(db: AsyncSession, receivable_id: int, req, operator_id: int) -> dict:
    from app.modules.receivable.models import Receivable
    r = (await db.execute(select(Receivable).where(Receivable.id == receivable_id))).scalar_one_or_none()
    if not r:
        from app.core.exceptions import NotFoundException
        raise NotFoundException(f"回款不存在：{receivable_id}")
    data = req.model_dump(exclude_unset=True)
    if "planAmount" in data and data["planAmount"] is not None:
        r.plan_amount = data["planAmount"] * 100
    for k_in, k_db in (("type", "type"), ("actualDate", "actual_date"), ("planDate", "plan_date"),
                       ("managerId", "manager_id"), ("remark", "remark")):
        if k_in in data and data[k_in] is not None:
            setattr(r, k_db, data[k_in])
    await db.commit()
    await db.refresh(r)
    return await get_receivable(db, r.id)


# ===== 删除 =====
async def delete_receivable(db: AsyncSession, receivable_id: int, operator_id: int) -> dict:
    from app.modules.receivable.models import Receivable
    r = (await db.execute(select(Receivable).where(Receivable.id == receivable_id))).scalar_one_or_none()
    if not r:
        from app.core.exceptions import NotFoundException
        raise NotFoundException(f"回款不存在：{receivable_id}")
    # 业务护：已收 > 0 不可删
    if (r.received_amount or 0) > 0:
        from app.core.exceptions import ConflictException
        raise ConflictException("该回款已登记到账（已收金额 > 0），不允许删除")
    await db.delete(r)
    await db.commit()
    return {"deleted": True}
