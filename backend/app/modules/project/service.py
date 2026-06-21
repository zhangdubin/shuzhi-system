"""
项目服务层
"""
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException, ConflictException
from app.modules.project.models import Project, ProjectMilestone
from app.modules.project.schemas import (
    ProjectCreate, ProjectUpdate, MilestoneCreate,
)


def _gen_project_code() -> str:
    """生成项目编号 PRJ-2026-XXX"""
    return f"PRJ-{datetime.now().year}-{uuid.uuid4().hex[:3].upper()}"


# ===== 列表 =====

async def list_projects(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    keyword: str = "",
    filters: dict = None,
    current_user = None,  # R11B data_scope 过滤
) -> tuple[list[dict], int]:
    """分页查询项目列表"""
    filters = filters or {}
    query = select(Project)
    # R11B 权限细化：data_scope 过滤（manager_id 关联 user.department_id）
    if current_user is not None:
        from app.core.data_scope import build_data_scope_filter_async
        query = await build_data_scope_filter_async(
            db, query, Project, current_user,
            owner_field=Project.manager_id,
            owner_via_user_dept=True,
        )

    conditions = []
    if keyword:
        conditions.append(or_(
            Project.name.ilike(f"%{keyword}%"),
            Project.code.ilike(f"%{keyword}%"),
        ))
    if filters.get("status"):
        conditions.append(Project.status == filters["status"])
    if filters.get("managerId"):
        conditions.append(Project.manager_id == filters["managerId"])
    if filters.get("clientId"):
        conditions.append(Project.client_id == filters["clientId"])
    if filters.get("type"):
        conditions.append(Project.type == filters["type"])
    # 金额区间（合同金额单位为分）
    if filters.get("amountMin") is not None:
        try: conditions.append(Project.contract_amount >= int(float(filters["amountMin"]) * 100))
        except: pass
    if filters.get("amountMax") is not None:
        try: conditions.append(Project.contract_amount <= int(float(filters["amountMax"]) * 100))
        except: pass

    if conditions:
        query = query.where(and_(*conditions))

    # 总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 列表（预加载 client/manager，避开后续响应阶段的 lazy IO）
    query = query.order_by(Project.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    query = query.options(selectinload(Project.client), selectinload(Project.manager))
    result = await db.execute(query)
    projects = result.scalars().all()

    # 关联查询
    list_data = []
    for p in projects:
        list_data.append({
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "type": p.type,
            "status": p.status,
            "clientId": p.client_id,
            "clientName": p.client.name if p.client else None,
            "managerId": p.manager_id,
            "managerName": p.manager.name if p.manager else None,
            "startDate": p.start_date,
            "endDate": p.end_date,
            "contractAmount": Decimal(p.contract_amount or 0) / 100,
            "budget": Decimal(p.budget or 0) / 100,
            "spent": Decimal(p.spent or 0) / 100,
            "progress": p.progress or 0,
            "description": p.description,
            "createdAt": p.created_at,
            "updatedAt": p.updated_at,
        })

    return list_data, total


# ===== 详情 =====

async def get_project(db: AsyncSession, project_id: int) -> dict:
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.client),
            selectinload(Project.manager),
            selectinload(Project.milestones),
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundException(f"项目不存在：{project_id}")

    return {
        "id": project.id,
        "code": project.code,
        "name": project.name,
        "type": project.type,
        "status": project.status,
        "clientId": project.client_id,
        "clientName": project.client.name if project.client else None,
        "managerId": project.manager_id,
        "managerName": project.manager.name if project.manager else None,
        "startDate": project.start_date,
        "endDate": project.end_date,
        "contractAmount": Decimal(project.contract_amount or 0) / 100,
        "budget": Decimal(project.budget or 0) / 100,
        "spent": Decimal(project.spent or 0) / 100,
        "progress": project.progress or 0,
        "description": project.description,
        "milestones": [
            {
                "id": m.id,
                "name": m.name,
                "seq": m.seq,
                "status": m.status,
                "plannedStart": m.planned_start,
                "plannedEnd": m.planned_end,
                "completedAt": m.completed_at,
                "progress": m.progress or 0,
                "remark": m.remark,
            }
            for m in sorted(project.milestones, key=lambda x: x.seq)
        ],
        "createdAt": project.created_at,
        "updatedAt": project.updated_at,
    }


# ===== 创建 =====

async def create_project(
    db: AsyncSession,
    req: ProjectCreate,
    creator_id: int,
) -> dict:
    # 检查同名（同一客户下）
    if req.clientId:
        existing = await db.execute(
            select(Project).where(
                Project.name == req.name,
                Project.client_id == req.clientId,
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictException(f"该项目名已存在")

    project = Project(
        code=req.code or _gen_project_code(),
        name=req.name,
        type=req.type,
        client_id=req.clientId,
        manager_id=req.managerId,
        start_date=req.startDate,
        end_date=req.endDate,
        # 前端传"元"，DB 存"分"（*100）
        contract_amount=(req.contractAmount or 0) * 100,
        budget=(req.budget or 0) * 100,
        spent=(req.spent or 0) * 100,
        progress=req.progress or 0,
        status=req.status or "planning",
        description=req.description,
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return await get_project(db, project.id)


# ===== 更新 =====

async def update_project(
    db: AsyncSession,
    project_id: int,
    req: ProjectUpdate,
) -> dict:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundException(f"项目不存在：{project_id}")

    update_data = req.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        # 字段名转换
        if k == "clientId":
            project.client_id = v
        elif k == "managerId":
            project.manager_id = v
        elif k == "startDate":
            project.start_date = v
        elif k == "endDate":
            project.end_date = v
        elif k == "budget":
            project.budget = v
        elif k == "spent":
            project.spent = v
        elif k == "progress":
            project.progress = v
        else:
            setattr(project, k, v)

    await db.commit()
    await db.refresh(project)
    return await get_project(db, project.id)


# ===== 删除 =====

async def delete_project(db: AsyncSession, project_id: int):
    from app.modules.contract.models import Contract
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundException(f"项目不存在：{project_id}")
    # 业务护：项目下有"审批中"合同不允许删
    approving_count = (await db.execute(
        select(func.count())
        .select_from(Contract)
        .where(Contract.project_id == project_id, Contract.status == 'approving')
    )).scalar() or 0
    if approving_count > 0:
        # 拿前 3 个 code 用于提示
        codes = (await db.execute(
            select(Contract.code).where(Contract.project_id == project_id, Contract.status == 'approving').limit(3)
        )).scalars().all()
        raise ConflictException(
            f"项目下有 {approving_count} 份审批中的合同（{', '.join(codes)}...），请先处理后再删除项目"
        )
    await db.delete(project)
    await db.commit()


# ===== 里程碑 =====

async def add_milestone(
    db: AsyncSession,
    project_id: int,
    req: MilestoneCreate,
) -> dict:
    result = await db.execute(
        select(Project)
        .where(Project.id == project_id)
        .options(selectinload(Project.milestones))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundException(f"项目不存在：{project_id}")

    # 计算下一个 seq
    seq = len(project.milestones) + 1

    ms = ProjectMilestone(
        project_id=project_id,
        name=req.name,
        seq=seq,
        status="todo",
        planned_start=req.plannedStart,
        planned_end=req.plannedEnd,
        operator_id=req.operatorId,
        remark=req.remark,
    )
    db.add(ms)
    await db.commit()
    await db.refresh(ms)

    return {
        "id": ms.id,
        "name": ms.name,
        "seq": ms.seq,
        "status": ms.status,
        "plannedStart": ms.planned_start,
        "plannedEnd": ms.planned_end,
        "progress": 0,
    }


# ===== 统计 =====

async def get_stats(db: AsyncSession) -> dict:
    """Dashboard 用的项目统计"""
    today = datetime.now().date()
    month_start = today.replace(day=1)
    soon = today + timedelta(days=30)

    active = await db.scalar(
        select(func.count()).where(Project.status == "in_progress")
    )
    new_month = await db.scalar(
        select(func.count()).where(
            Project.created_at >= datetime.combine(month_start, datetime.min.time())
        )
    )
    completed_month = await db.scalar(
        select(func.count()).where(
            Project.status == "completed",
            Project.updated_at >= datetime.combine(month_start, datetime.min.time()),
        )
    )
    expiring = await db.scalar(
        select(func.count()).where(
            Project.status == "in_progress",
            Project.end_date != None,
            Project.end_date <= soon,
            Project.end_date >= today,
        )
    )
    total_amount = await db.scalar(
        select(func.sum(Project.contract_amount)).where(
            Project.status.in_(["in_progress", "completed"])
        )
    )

    return {
        "active": active or 0,
        "newThisMonth": new_month or 0,
        "completedThisMonth": completed_month or 0,
        "expiringSoon": expiring or 0,
        "totalContractAmount": Decimal(total_amount or 0) / 100,
    }
