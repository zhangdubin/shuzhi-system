"""
合同模块服务层
"""
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException, ParamErrorException, ConflictException
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
