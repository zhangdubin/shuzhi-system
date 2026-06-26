"""
公共模块服务层
- 字典查询 / 用户引用 / 客户引用 / 合同&项目引用 / 文件保存
"""
import io
import secrets
import string
from datetime import datetime
from typing import Optional

from fastapi import UploadFile
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.auth.models import User, Department
from app.modules.auth.schemas import UserInfo as _UserInfo
from app.modules.common.models import File as FileModel, Client
from app.modules.common.schemas import (
    DictItem, DictListResponse, UserBrief, UserListResponse,
    ClientBrief, ClientListResponse, ContractRef, ProjectRef, FileInfo,
)
# 注意：不要在这里 import contract.models / project.models
# 会在 common -> contract -> project -> common 链上形成循环
# 改在函数内延迟 import（见下面 list_contracts_ref / list_projects_ref）


# ===== 字典 =====

async def list_dict(db: AsyncSession, dict_type: str) -> DictListResponse:
    """按 dict_type 查字典值（来自 dictionaries 表）"""
    from app.modules.auth.models import Dictionary
    result = await db.execute(
        select(Dictionary)
        .where(Dictionary.dict_type == dict_type, Dictionary.is_active == True)
        .order_by(Dictionary.sort.asc(), Dictionary.id.asc())
    )
    items = [
        DictItem(value=d.value, label=d.label, color=d.color)
        for d in result.scalars().all()
    ]
    return DictListResponse(list=items)


# ===== 用户引用 =====

async def list_users(
    db: AsyncSession,
    keyword: str = "",
    department_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
) -> UserListResponse:
    query = select(User).where(User.is_active == True)
    if keyword:
        query = query.where(
            or_(
                User.name.ilike(f"%{keyword}%"),
                User.username.ilike(f"%{keyword}%"),
                User.email.ilike(f"%{keyword}%"),
            )
        )
    if department_id:
        query = query.where(User.department_id == department_id)
    count_q = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_q)).scalar() or 0
    query = query.options(selectinload(User.department), selectinload(User.roles))
    query = query.order_by(User.id.asc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()

    items: list[UserBrief] = []
    for u in rows:
        role = u.roles[0].name if u.roles else None
        items.append(UserBrief(
            userId=u.id, name=u.name, avatar=u.avatar,
            department=u.department.name if u.department else None,
            role=role,
        ))
    return UserListResponse(list=items, total=total, page=page, pageSize=page_size)


# ===== 客户引用 =====

async def list_clients(
    db: AsyncSession, keyword: str = "", page: int = 1, page_size: int = 50,
    include_inactive: bool = False,
    level: str | None = None,
    industry: str | None = None,
) -> ClientListResponse:
    """客户列表（含全部档案字段 + 合同金额/数量聚合）

    - 默认只显示启用客户（is_active=True）；include_inactive=True 时不过滤
    - level 字段保持 A/B/C/D 字符（与 Client 表一致）
    - contractCount / totalAmount 在内存中按 client_id 聚合，
      避免每行 N+1 查询
    """
    # 延迟 import：合同表在 contract 模块，避免循环
    from app.modules.contract.models import Contract
    from decimal import Decimal

    query = select(Client)
    if not include_inactive:
        query = query.where(Client.is_active == True)
    if keyword:
        query = query.where(
            or_(Client.name.ilike(f"%{keyword}%"), Client.code.ilike(f"%{keyword}%"))
        )
    if level:
        query = query.where(Client.level == level)
    if industry:
        query = query.where(Client.industry == industry)
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = query.order_by(Client.id.asc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()

    # 一次聚合：取当前页所有客户的合同数和金额合计
    client_ids = [c.id for c in rows]
    agg_map: dict[int, dict] = {cid: {"count": 0, "amount": 0.0} for cid in client_ids}
    if client_ids:
        agg_rows = (await db.execute(
            select(
                Contract.client_id,
                func.count(Contract.id),
                func.coalesce(func.sum(Contract.amount), 0),
            )
            .where(Contract.client_id.in_(client_ids))
            .group_by(Contract.client_id)
        )).all()
        for cid, cnt, amt in agg_rows:
            agg_map[cid] = {"count": int(cnt or 0), "amount": float(Decimal(amt or 0) / 100)}

    items = [
        ClientBrief(
            id=c.id,
            clientId=c.id,
            code=c.code,
            name=c.name,
            shortName=c.short_name,
            taxNo=c.tax_no,
            legalPerson=c.legal_person,
            contactName=c.contact_name,
            contactPhone=c.contact_phone,
            contactEmail=c.contact_email,
            address=c.address,
            bankName=c.bank_name,
            bankAccount=c.bank_account,
            industry=c.industry,
            level=c.level or "C",
            isActive=bool(c.is_active),
            remark=c.remark,
            createdAt=c.created_at.isoformat() if c.created_at else None,
            contractCount=agg_map.get(c.id, {}).get("count", 0),
            totalAmount=agg_map.get(c.id, {}).get("amount", 0.0),
        )
        for c in rows
    ]
    return ClientListResponse(list=items, total=total, page=page, pageSize=page_size)


async def get_client_stats(db: AsyncSession) -> dict:
    """客户统计卡：总数（含停用）/ 活跃 / VIP / 合同总金额

    返回字段：
    - totalAll / total: 含停用的全部客户数
    - active / totalActive: 仅启用客户数
    - inactive: 已停用客户数
    - vip: A 级且启用
    - contractAmount / contractCount: 全部合同
    """
    from app.modules.contract.models import Contract
    from decimal import Decimal

    total_all = (await db.execute(select(func.count()).select_from(Client))).scalar() or 0
    active = (await db.execute(
        select(func.count()).select_from(Client).where(Client.is_active == True)
    )).scalar() or 0
    vip = (await db.execute(
        select(func.count()).select_from(Client).where(Client.level == "A", Client.is_active == True)
    )).scalar() or 0
    contract_total = (await db.execute(
        select(func.coalesce(func.sum(Contract.amount), 0))
    )).scalar() or 0
    contract_count = (await db.execute(select(func.count()).select_from(Contract))).scalar() or 0
    total = int(total_all)
    inactive = max(0, total - int(active))
    return {
        # 兼容旧字段：total = 全部客户
        "total": total,
        "totalAll": total,
        "active": int(active),
        "totalActive": int(active),
        "inactive": inactive,
        "vip": int(vip),
        "contractAmount": float(Decimal(contract_total) / 100),
        "contractCount": int(contract_count),
    }


# ===== 合同/项目引用（按客户过滤） =====

async def list_contracts_ref(
    db: AsyncSession,
    client_id: Optional[int] = None,
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
) -> list[ContractRef]:
    from decimal import Decimal
    # 延迟 import，避免 common -> contract -> project -> common 循环
    from app.modules.contract.models import Contract
    query = select(Contract)
    if client_id:
        query = query.where(Contract.client_id == client_id)
    if keyword:
        query = query.where(
            or_(Contract.name.ilike(f"%{keyword}%"), Contract.code.ilike(f"%{keyword}%"))
        )
    query = query.order_by(Contract.id.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()
    return [
        ContractRef(
            contractId=c.id, code=c.code, name=c.name, type=c.type,
            amount=float(Decimal(c.amount or 0) / 100),
            status=c.status, signDate=c.sign_date.isoformat() if c.sign_date else None,
        )
        for c in rows
    ]


async def list_projects_ref(
    db: AsyncSession,
    client_id: Optional[int] = None,
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
) -> list[ProjectRef]:
    # 延迟 import
    from app.modules.project.models import Project
    query = select(Project).options(selectinload(Project.manager))
    if client_id:
        query = query.where(Project.client_id == client_id)
    if keyword:
        query = query.where(
            or_(Project.name.ilike(f"%{keyword}%"), Project.code.ilike(f"%{keyword}%"))
        )
    query = query.order_by(Project.id.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()
    return [
        ProjectRef(
            projectId=p.id, code=p.code, name=p.name, status=p.status,
            managerName=p.manager.name if p.manager else None,
        )
        for p in rows
    ]


# ===== 文件保存 =====

async def save_upload_file(
    db: AsyncSession, uploader_id: int, file: UploadFile
) -> FileInfo:
    """保存上传文件 + 写 files 表"""
    from app.integrations.storage import save_file as _save  # 业务代码不直接依赖 storage

    content = await file.read()
    info = await _save(file.filename or "unnamed", content)

    rec = FileModel(
        id=info["fileId"],
        name=info["name"],
        ext=info["ext"],
        size=info["size"],
        mime_type=info["mimeType"],
        url=info["url"],
        storage=info.get("storage", "local"),
        uploader_id=uploader_id,
    )
    db.add(rec)
    await db.commit()

    return FileInfo(fileId=info["fileId"], name=info["name"], size=info["size"], url=info["url"])
