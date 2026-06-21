"""
项目模块路由
对应 API.md §项目管理 5 个接口
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_permission, CurrentUser
from app.modules.project import service
from app.modules.project.schemas import (
    ProjectListRequest, ProjectUpdate,
    MilestoneCreate, ProjectCreate,
)

router = APIRouter()


@router.post("/list", summary="项目列表（分页）")
async def list_projects(
    req: ProjectListRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    list_data, total = await service.list_projects(
        db, req.page, req.pageSize, req.keyword, req.filters, current_user=current_user
    )
    return {
        "code": 0,
        "data": {
            "list": list_data,
            "total": total,
            "page": req.page,
            "pageSize": req.pageSize,
        }
    }


@router.post("/detail", summary="项目详情")
async def get_project(
    projectId: int = Query(..., description="项目 ID"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    project = await service.get_project(db, projectId)
    return {"code": 0, "data": project}


@router.post("/create", summary="项目立项")
async def create_project(
    req: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("project:write")),
):
    project = await service.create_project(db, req, current_user.id)
    return {"code": 0, "data": project, "message": "立项成功"}


@router.post("/update", summary="更新项目")
async def update_project(
    projectId: int = Query(...),
    req: ProjectUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("project:write")),
):
    project = await service.update_project(db, projectId, req)
    return {"code": 0, "data": project, "message": "更新成功"}


@router.post("/delete", summary="删除项目")
async def delete_project(
    projectId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("project:write")),
):
    await service.delete_project(db, projectId)
    return {"code": 0, "message": "删除成功"}


# ===== 里程碑 =====

@router.post("/milestone/add", summary="添加里程碑")
async def add_milestone(
    projectId: int = Query(...),
    req: MilestoneCreate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("milestone:write")),
):
    ms = await service.add_milestone(db, projectId, req)
    return {"code": 0, "data": ms, "message": "添加成功"}


# ===== 统计 =====

@router.post("/stats", summary="项目统计（Dashboard 用）")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    stats = await service.get_stats(db)
    return {"code": 0, "data": stats}
