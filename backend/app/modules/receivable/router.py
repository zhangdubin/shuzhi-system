"""
回款路由
- /api/v1/receivables/*
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_permission, CurrentUser
from app.core.sse import publish_event
from app.modules.receivable import service
from app.modules.receivable.schemas import (
    ReceivableListRequest, ReceivableCreate, ReceivableUpdate, ReceivableRemindRequest, ReceivableReceiveRequest,
)


router = APIRouter()


@router.post("/list", summary="回款列表")
async def list_receivables(
    req: ReceivableListRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    items, total = await service.list_receivables(
        db, req.page, req.pageSize, req.keyword, req.filters, current_user=current_user
    )
    return {"code": 0, "data": {"list": items, "total": total, "page": req.page, "pageSize": req.pageSize}}


@router.post("/detail", summary="回款详情")
async def get_receivable(
    receivableId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.get_receivable(db, receivableId)
    return {"code": 0, "data": data}


@router.post("/create", summary="创建回款计划")
async def create_receivable(
    req: ReceivableCreate,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("receivable:write")),
):
    data = await service.create_receivable(db, req)
    return {"code": 0, "data": data, "message": "回款计划已创建"}


@router.post("/remind", summary="登记催收")
async def remind(
    req: ReceivableRemindRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    data = await service.add_remind(db, req, current_user.id)
    await publish_event("sse:dashboard", "activity", {
        "type": "回款", "action": "催收", "operator": current_user.name,
        "title": f"{current_user.name} 发起回款催收 #{req.receivableId}",
    })
    return {"code": 0, "data": data, "message": "催收记录已添加"}


@router.post("/receive", summary="登记到账")
async def receive(
    req: ReceivableReceiveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    data = await service.receive_payment(db, req, current_user.id)
    amt_yuan = (req.receivedAmount or 0) / 100
    await publish_event("sse:dashboard", "activity", {
        "type": "回款", "action": "到账", "operator": current_user.name,
        "title": f"{current_user.name} 登记到账 ¥{amt_yuan:.2f}",
    })
    return {"code": 0, "data": data, "message": "已登记到账"}


@router.post("/update", summary="编辑回款")
async def update_receivable(
    receivableId: int = Query(...),
    req: ReceivableUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    data = await service.update_receivable(db, receivableId, req, current_user.id)
    return {"code": 0, "data": data, "message": "已更新"}


@router.post("/delete", summary="删除回款")
async def delete_receivable(
    receivableId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    data = await service.delete_receivable(db, receivableId, current_user.id)
    return {"code": 0, "data": data, "message": "已删除"}


@router.post("/stats", summary="回款统计（Dashboard 用）")
async def stats(
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.get_stats(db)
    return {"code": 0, "data": data}
