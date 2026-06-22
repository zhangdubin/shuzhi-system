"""
销售费用路由
- /api/v1/expenses/*
"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_permission, CurrentUser
from app.core.sse import publish_event
from app.modules.expense import service
from app.modules.expense.schemas import (
    ExpenseListRequest, ExpenseCreate, ExpenseUpdate, ExpenseApproveRequest,
)


router = APIRouter()


@router.post("/list", summary="费用列表")
async def list_expenses(
    req: ExpenseListRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    items, total = await service.list_expenses(
        db, req.page, req.pageSize, req.keyword, req.filters, current_user=current_user
    )
    return {"code": 0, "data": {"list": items, "total": total, "page": req.page, "pageSize": req.pageSize}}


@router.post("/detail", summary="费用详情")
async def get_expense(
    expenseId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.get_expense(db, expenseId)
    return {"code": 0, "data": data}


@router.post("/create", summary="录入费用")
async def create_expense(
    req: ExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("expense:write")),
):
    data = await service.create_expense(db, req, current_user.id)
    await publish_event("sse:dashboard", "activity", {
        "type": "费用", "action": "录入", "operator": current_user.name,
        "title": f"{current_user.name} 录入费用 ¥{req.amount/100:.0f}",
    })
    return {"code": 0, "data": data, "message": "已保存草稿"}


@router.post("/update", summary="编辑费用")
async def update_expense(
    expenseId: int = Query(...),
    req: ExpenseUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("expense:write")),
):
    data = await service.update_expense(db, expenseId, req, current_user.id)
    await publish_event("sse:dashboard", "activity", {
        "type": "费用", "action": "编辑", "operator": current_user.name,
        "title": f"{current_user.name} 编辑费用 #{expenseId}",
    })
    return {"code": 0, "data": data, "message": "已更新"}


@router.post("/delete", summary="删除费用")
async def delete_expense(
    expenseId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("expense:delete")),
):
    data = await service.delete_expense(db, expenseId, current_user.id)
    await publish_event("sse:dashboard", "activity", {
        "type": "费用", "action": "删除", "operator": current_user.name,
        "title": f"{current_user.name} 删除费用 #{expenseId}",
    })
    return {"code": 0, "data": data, "message": "已删除"}


class BatchDeleteRequest(BaseModel):
    expenseIds: list[int]


@router.post("/batch/delete", summary="批量删除费用（仅超管）")
async def batch_delete_expenses(
    req: BatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("expense:delete")),
):
    data = await service.batch_delete_expenses(db, req.expenseIds, current_user.id)
    await publish_event("sse:dashboard", "activity", {
        "type": "费用", "action": "批量删除", "operator": current_user.name,
        "title": f"{current_user.name} 批量删除费用 {data['deleted']} 条",
    })
    msg = f"已删除 {data['deleted']} 条"
    if data.get("skipped"):
        msg += f"，跳过 {len(data['skipped'])} 条（被报销单引用，不能删除）"
    return {"code": 0, "data": data, "message": msg}


@router.post("/submit", summary="提交审批（draft → pending）")
async def submit_expense(
    expenseId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    data = await service.submit_expense(db, expenseId, current_user.id)
    await publish_event("sse:dashboard", "activity", {
        "type": "费用", "action": "提交审批", "operator": current_user.name,
        "title": f"{current_user.name} 提交费用审批 #{expenseId}",
    })
    return {"code": 0, "data": data, "message": "已提交审批"}


@router.post("/mark-paid", summary="确认报销（approved → paid）")
async def mark_paid(
    expenseId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("expense:write")),
):
    data = await service.mark_paid(db, expenseId, current_user.id)
    await publish_event("sse:dashboard", "activity", {
        "type": "费用", "action": "确认报销", "operator": current_user.name,
        "title": f"{current_user.name} 确认报销 #{expenseId}",
    })
    return {"code": 0, "data": data, "message": "已确认报销"}


@router.post("/approve", summary="审批费用")
async def approve_expense(
    req: ExpenseApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("expense:approve")),
):
    data = await service.approve_expense(db, req, current_user.id)
    action = {"approve": "通过", "reject": "驳回", "transfer": "转交"}.get(req.action, "审批")
    await publish_event("sse:dashboard", "activity", {
        "type": "费用", "action": f"审批{action}", "operator": current_user.name,
        "title": f"{current_user.name} {action}费用 #{req.expenseId}",
    })
    return {"code": 0, "data": data, "message": "审批完成"}


@router.post("/stats", summary="费用统计（Dashboard 用）")
async def stats(
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.get_stats(db)
    return {"code": 0, "data": data}
