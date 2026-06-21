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
    db: AsyncSession, keyword: str = "", page: int = 1, page_size: int = 50
) -> ClientListResponse:
    query = select(Client).where(Client.is_active == True)
    if keyword:
        query = query.where(
            or_(Client.name.ilike(f"%{keyword}%"), Client.code.ilike(f"%{keyword}%"))
        )
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = query.order_by(Client.id.asc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()
    items = [
        ClientBrief(
            clientId=c.id, code=c.code, name=c.name,
            shortName=c.short_name, taxNo=c.tax_no, level=c.level,
        )
        for c in rows
    ]
    return ClientListResponse(list=items, total=total, page=page, pageSize=page_size)


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
        storage="local",
        uploader_id=uploader_id,
    )
    db.add(rec)
    await db.commit()

    return FileInfo(fileId=info["fileId"], name=info["name"], size=info["size"], url=info["url"])
