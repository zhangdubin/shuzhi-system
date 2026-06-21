"""
Dashboard 路由
- /api/v1/dashboard/*
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, CurrentUser
from app.modules.dashboard import service


router = APIRouter()


@router.post("/summary", summary="首页数据汇总")
async def summary(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    data = await service.summary(db, current_user.user)
    return {"code": 0, "data": data}


@router.post("/activities", summary="最近活动")
async def activities(
    page: int = 1,
    pageSize: int = 10,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.activities(db, page, pageSize)
    return {"code": 0, "data": data}
