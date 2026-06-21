"""
销售费用服务层
"""
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException, ParamErrorException, ConflictException
from app.modules.expense.models import Expense, ExpenseBreakdown
from app.modules.expense.schemas import (
    ExpenseCreate, ExpenseApproveRequest, ExpenseBreakdownItem,
)
from app.modules.auth.models import User, Department
from app.modules.common.approvals import create_flow, act as act_flow, get_flow, serialize_flow


def _gen_expense_code() -> str:
    return f"EX-{datetime.now().year}-{uuid.uuid4().hex[:3].upper()}"


# ===== 列表 =====
async def list_expenses(
    db: AsyncSession, page: int = 1, page_size: int = 20,
    keyword: str = "", filters: dict = None,
    current_user = None,  # R11B data_scope 过滤
) -> tuple[list[dict], int]:
    filters = filters or {}
    query = select(Expense)
    # R11B 权限细化：data_scope 过滤（直接用 department_id 字段）
    if current_user is not None:
        from app.core.data_scope import build_data_scope_filter_async
        query = await build_data_scope_filter_async(
            db, query, Expense, current_user,
            direct_dept_field=Expense.department_id,
            owner_field=Expense.applicant_id,  # self 范围用
        )
    if keyword:
        query = query.where(or_(Expense.title.ilike(f"%{keyword}%"), Expense.code.ilike(f"%{keyword}%")))
    if filters.get("category"):
        query = query.where(Expense.category == filters["category"])
    if filters.get("status"):
        query = query.where(Expense.status == filters["status"])
    if filters.get("applicantId"):
        query = query.where(Expense.applicant_id == int(filters["applicantId"]))
    if filters.get("departmentId"):
        query = query.where(Expense.department_id == int(filters["departmentId"]))
    dr = filters.get("dateRange")
    if dr and isinstance(dr, list) and len(dr) == 2:
        try:
            d1 = date.fromisoformat(dr[0]); d2 = date.fromisoformat(dr[1])
            query = query.where(Expense.expense_date >= d1, Expense.expense_date <= d2)
        except Exception:
            pass

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = query.options(
        selectinload(Expense.applicant), selectinload(Expense.department),
    ).order_by(Expense.id.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()

    items = []
    for e in rows:
        amount_yuan = float(Decimal(e.amount or 0) / 100)
        # AI 风险规则引擎（轻量 mock）
        ai_tags: list[str] = []
        ai_suggestion: str | None = None
        ai_risk: str = "low"  # low / medium / high
        ai_reason: str = ""
        # 1. 高额（>5万）
        if amount_yuan >= 50000:
            ai_tags.append("高额报销")
            ai_suggestion = "review"
            if ai_risk == "low": ai_risk = "medium"
            ai_reason = f"金额 ¥{amount_yuan:,.0f} 超过 5 万，建议复核"
        # 2. 超额（>10万）
        if amount_yuan >= 100000:
            ai_tags.append("超额")
            ai_suggestion = "risk"
            ai_risk = "high"
            ai_reason = f"金额 ¥{amount_yuan:,.0f} 超过 10 万，需财务总监审批"
        # 3. 标题过短（疑似测试数据）
        if not e.title or len(e.title.strip()) <= 2:
            ai_tags.append("事由不清")
            if not ai_suggestion: ai_suggestion = "review"
            if ai_risk == "low": ai_risk = "medium"
            ai_reason = (ai_reason + "; " if ai_reason else "") + "事由内容过短，需补充说明"
        # 4. 招待类目 + 高额
        if e.category == "招待" and amount_yuan >= 5000:
            ai_tags.append("招待高额")
            if not ai_suggestion: ai_suggestion = "review"
            if ai_risk == "low": ai_risk = "medium"
            ai_reason = (ai_reason + "; " if ai_reason else "") + "招待类目高额，建议核对发票"
        # 5. 差旅 + 周五/周末提交
        try:
            if e.expense_date and e.expense_date.weekday() in (4, 5, 6) and e.category == "差旅":
                ai_tags.append("周末差旅")
                if not ai_suggestion: ai_suggestion = "review"
                ai_reason = (ai_reason + "; " if ai_reason else "") + "周末差旅，建议确认行程"
        except Exception:
            pass
        # 6. 审批中超过 3 天
        if e.status == "pending" and e.submit_at:
            try:
                from datetime import datetime, timezone
                days = (datetime.utcnow() - e.submit_at).days
                if days >= 3:
                    ai_tags.append("审批滞留")
                    if not ai_suggestion: ai_suggestion = "review"
                    ai_reason = (ai_reason + "; " if ai_reason else "") + f"已审批 {days} 天，建议催办"
            except Exception:
                pass
        # 默认通过建议
        if not ai_suggestion:
            ai_suggestion = "approve"
            ai_reason = "AI 检测无异常"
        if not ai_tags:
            ai_tags.append("正常")

        items.append({
            "expenseId": e.id, "code": e.code, "category": e.category, "title": e.title,
            "amount": amount_yuan, "currency": e.currency,
            "expenseDate": e.expense_date,
            "applicantId": e.applicant_id, "applicantName": e.applicant.name if e.applicant else "",
            "departmentId": e.department_id, "departmentName": e.department.name if e.department else None,
            "status": e.status, "submitAt": e.submit_at, "createdAt": e.created_at,
            "aiTags": ai_tags,
            "aiSuggestion": ai_suggestion,
            "aiRisk": ai_risk,
            "aiReason": ai_reason,
        })
    return items, total


# ===== 详情 =====
async def get_expense(db: AsyncSession, expense_id: int) -> dict:
    e = (await db.execute(
        select(Expense).where(Expense.id == expense_id)
        .options(
            selectinload(Expense.applicant), selectinload(Expense.department),
            selectinload(Expense.breakdowns),
        )
    )).scalar_one_or_none()
    if not e:
        raise NotFoundException(f"费用不存在：{expense_id}")

    flow = await get_flow(db, "expense", e.id)
    approval = serialize_flow(flow, getattr(flow, "_steps_cache", [])) if flow else None

    return {
        "expenseId": e.id, "code": e.code, "category": e.category, "title": e.title,
        "description": e.description,
        "amount": Decimal(e.amount or 0) / 100, "currency": e.currency,
        "expenseDate": e.expense_date, "submitDate": e.submit_at,
        "applicant": {"userId": e.applicant.id, "name": e.applicant.name, "avatar": e.applicant.avatar} if e.applicant else None,
        "department": {"id": e.department.id, "name": e.department.name} if e.department else None,
        "contractId": e.contract_id, "projectId": e.project_id,
        "breakdown": [
            {"label": b.label, "amount": Decimal(b.amount or 0) / 100, "remark": b.remark}
            for b in e.breakdowns
        ],
        "attachments": [],
        "approvalFlow": approval,
        "status": e.status, "createdAt": e.created_at, "updatedAt": e.updated_at,
    }


# ===== 创建 =====
async def create_expense(db: AsyncSession, req: ExpenseCreate, applicant_id: int) -> dict:
    # 找部门
    u = (await db.execute(select(User).where(User.id == applicant_id))).scalar_one_or_none()
    department_id = u.department_id if u else None

    e = Expense(
        code=_gen_expense_code(),
        category=req.category, title=req.title, description=req.description,
        # 前端传"元"，DB 存"分"（*100）
        amount=req.amount * 100, currency="CNY", expense_date=req.expenseDate,
        applicant_id=applicant_id, department_id=department_id,
        contract_id=req.contractId, project_id=req.projectId,
        cost_center=None, status="draft",
    )
    db.add(e)
    await db.flush()

    for b in req.breakdown:
        # amount 是分
        cents = int((Decimal(b.amount) * 100).quantize(Decimal("1"))) if isinstance(b.amount, (int, float, Decimal)) else int(b.amount)
        db.add(ExpenseBreakdown(
            expense_id=e.id, label=b.label, amount=cents, remark=b.remark,
        ))
    await db.commit()
    await db.refresh(e)
    return await get_expense(db, e.id)


# ===== 提交审批 =====
async def submit_expense(db: AsyncSession, expense_id: int, user_id: int) -> dict:
    e = (await db.execute(select(Expense).where(Expense.id == expense_id))).scalar_one_or_none()
    if not e:
        raise NotFoundException(f"费用不存在：{expense_id}")
    if e.status != "draft":
        raise ConflictException(f"只有 draft 状态可提交，当前 {e.status}")
    rules = ["submitter", "direct_leader", "finance"]
    if e.amount >= 500000:  # 5 千元
        rules.append("gm_if_over_5000")
    await create_flow(db, "expense", e.id, rules, user_id, e.amount)
    e.status = "pending"
    e.submit_at = datetime.utcnow()
    await db.commit()
    return await get_expense(db, e.id)


# ===== 确认报销（approved → paid）=====
async def mark_paid(db: AsyncSession, expense_id: int, operator_id: int) -> dict:
    e = (await db.execute(select(Expense).where(Expense.id == expense_id))).scalar_one_or_none()
    if not e:
        raise NotFoundException(f"费用不存在：{expense_id}")
    if e.status != "approved":
        raise ConflictException(f"只有「已通过」状态可确认报销，当前 {e.status}")
    e.status = "paid"
    e.finish_at = datetime.utcnow()
    await db.commit()
    return await get_expense(db, e.id)


# ===== 审批 =====
async def approve_expense(
    db: AsyncSession, req: ExpenseApproveRequest, operator_id: int
) -> dict:
    e = (await db.execute(select(Expense).where(Expense.id == req.expenseId))).scalar_one_or_none()
    if not e:
        raise NotFoundException(f"费用不存在：{req.expenseId}")
    flow = await get_flow(db, "expense", e.id)
    if not flow:
        raise NotFoundException("未找到审批流")
    await act_flow(db, flow.id, req.action, operator_id, req.comment, req.transferTo)
    await db.refresh(flow)
    if flow.status == "approved":
        e.status = "approved"
    elif flow.status == "rejected":
        e.status = "draft"
    await db.commit()
    return await get_expense(db, e.id)


# ===== 统计 =====
async def get_stats(db: AsyncSession) -> dict:
    total = (await db.execute(select(func.coalesce(func.sum(Expense.amount), 0)))).scalar() or 0
    pending_count = (await db.execute(select(func.count()).where(Expense.status == "pending"))).scalar() or 0
    pending_amt = (await db.execute(
        select(func.coalesce(func.sum(Expense.amount), 0)).where(Expense.status == "pending")
    )).scalar() or 0
    approved_count = (await db.execute(select(func.count()).where(Expense.status == "approved"))).scalar() or 0
    rejected_count = (await db.execute(select(func.count()).where(Expense.status == "rejected"))).scalar() or 0

    # 类目分布
    cat_rows = (await db.execute(
        select(Expense.category, func.coalesce(func.sum(Expense.amount), 0))
        .group_by(Expense.category)
    )).all()
    palette = {"差旅": "#4F6BFF", "招待": "#7C3AED", "办公": "#10B981", "推广": "#F59E0B", "培训": "#8B5CF6", "其他": "#94A3B8"}
    total_amt_for_ratio = sum([float(c) for _, c in cat_rows]) or 1
    category_chart = [
        {"name": cat, "amount": float(Decimal(amt) / 100), "ratio": round(float(amt) / total_amt_for_ratio, 2), "color": palette.get(cat, "#94A3B8")}
        for cat, amt in cat_rows
    ]

    return {
        "kpi": {
            "totalAmount": Decimal(total) / 100,
            "pendingCount": pending_count,
            "pendingAmount": Decimal(pending_amt) / 100,
            "approvedCount": approved_count,
            "rejectedCount": rejected_count,
        },
        "trendChart": {
            "labels": ["06-01", "06-08", "06-15", "06-22", "今天"],
            "actual": [180000, 150000, 130000, 95000, 60000],  # 占位
            "budgetLine": 2000000,
        },
        "categoryChart": category_chart,
    }

# ===== 更新 =====
async def update_expense(db: AsyncSession, expense_id: int, req, operator_id: int) -> dict:
    from app.modules.expense.models import Expense
    e = (await db.execute(select(Expense).where(Expense.id == expense_id))).scalar_one_or_none()
    if not e:
        from app.core.exceptions import NotFoundException
        raise NotFoundException(f"费用不存在：{expense_id}")
    # 业务护：approved/paid 不可改
    if e.status in ("approved", "paid"):
        from app.core.exceptions import ConflictException
        raise ConflictException(f"费用状态为「{e.status}」不允许编辑")
    data = req.model_dump(exclude_unset=True)
    if "amount" in data and data["amount"] is not None:
        e.amount = data["amount"] * 100  # 元 → 分
    for k in ("category", "title", "description", "expenseDate", "contractId", "projectId"):
        if k in data and data[k] is not None:
            setattr(e, k, data[k])
    await db.commit()
    await db.refresh(e)
    return await get_expense(db, e.id)


# ===== 删除 =====
async def delete_expense(db: AsyncSession, expense_id: int, operator_id: int) -> dict:
    from app.modules.expense.models import Expense
    e = (await db.execute(select(Expense).where(Expense.id == expense_id))).scalar_one_or_none()
    if not e:
        from app.core.exceptions import NotFoundException
        raise NotFoundException(f"费用不存在：{expense_id}")
    # 业务护：approved/paid 不可删
    if e.status in ("approved", "paid"):
        from app.core.exceptions import ConflictException
        raise ConflictException(f"费用状态为「{e.status}」不允许删除")
    await db.delete(e)
    await db.commit()
    return {"deleted": True}

