"""
合同模块路由
- /api/v1/contracts/*
"""
from fastapi import APIRouter, Depends, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_permission, CurrentUser
from app.core.sse import publish_event
from app.modules.contract import service
from app.modules.contract.schemas import (
    ContractListRequest, ContractCreate, ContractUpdate, ContractApproveRequest,
    ContractBatchDeleteRequest, ContractUrgeRequest,
)


router = APIRouter()


# ===== SSE 通知辅助 =====
async def _notify_dashboard(action: str, resource_type: str, operator: str, **extra):
    """写操作后发 dashboard SSE 事件"""
    await publish_event("sse:dashboard", "activity", {
        "type": resource_type,
        "action": action,
        "operator": operator,
        "title": f"{operator} {action} {resource_type}",
        **extra,
    })


@router.post("/list", summary="合同列表")
async def list_contracts(
    req: ContractListRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    items, total = await service.list_contracts(
        db, req.page, req.pageSize, req.keyword, req.filters, current_user=current_user
    )
    return {"code": 0, "data": {"list": items, "total": total, "page": req.page, "pageSize": req.pageSize}}


@router.post("/detail", summary="合同详情")
async def get_contract(
    contractId: int = Query(..., description="合同 ID"),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.get_contract(db, contractId)
    return {"code": 0, "data": data}


@router.post("/create", summary="新建合同")
async def create_contract(
    req: ContractCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("contract:write")),
):
    data = await service.create_contract(db, req, current_user.id)
    await _notify_dashboard("新建", "合同", current_user.name, code=data.get("code", ""))
    return {"code": 0, "data": data, "message": "创建成功"}


@router.post("/update", summary="更新合同（仅 draft）")
async def update_contract(
    contractId: int = Query(...),
    req: ContractUpdate = ...,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("contract:write")),
):
    data = await service.update_contract(db, contractId, req)
    await _notify_dashboard("更新", "合同", _user.name, contractId=contractId)
    return {"code": 0, "data": data, "message": "更新成功"}


@router.post("/delete", summary="删除合同（仅 draft/expired/archived 等状态）")
async def delete_contract(
    contractId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("contract:write")),
):
    await service.delete_contract(db, contractId)
    await _notify_dashboard("删除", "合同", _user.name, contractId=contractId)
    return {"code": 0, "message": "删除成功"}


@router.post("/batch/delete", summary="批量删除合同")
async def batch_delete_contracts(
    req: ContractBatchDeleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("contract:write")),
):
    data = await service.batch_delete_contracts(db, req.contractIds)
    await _notify_dashboard("批量删除", "合同", current_user.name, deleted=data["deleted"])
    msg = f"已删除 {data['deleted']} 条"
    if data.get("skipped"):
        msg += f"，跳过 {len(data['skipped'])} 条（状态不允许删除）"
    return {"code": 0, "data": data, "message": msg}


@router.post("/submit", summary="提交审批（draft → approving）")
async def submit_contract(
    contractId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    data = await service.submit_for_approval(db, contractId, current_user.id)
    await _notify_dashboard("提交审批", "合同", current_user.name, contractId=contractId)
    return {"code": 0, "data": data, "message": "已提交审批"}


@router.post("/approve", summary="审批合同（approve/reject/transfer）")
async def approve_contract(
    req: ContractApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("contract:approve")),
):
    data = await service.approve_contract(db, req, current_user.id)
    await _notify_dashboard(
        "审批" + (req.action == "approve" and "通过" or req.action == "reject" and "驳回" or "转交"),
        "合同", current_user.name, contractId=req.contractId,
    )
    return {"code": 0, "data": data, "message": "审批完成"}


@router.post("/stats", summary="合同统计（Dashboard 用）")
async def stats(
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.get_stats(db)
    return {"code": 0, "data": data}


@router.post("/template", summary="合同模板列表（起草时选用）")
async def list_templates(
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    items = await service.list_contract_templates(db)
    return {"code": 0, "data": {"templates": items}}


@router.post("/urge", summary="催办合同（仅审批中状态）")
async def urge_contract(
    req: ContractUrgeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    data = await service.urge_contract(
        db, req.contractId, current_user.id, current_user.name,
        message=req.message, target_user_ids=req.targetUserIds,
    )
    await _notify_dashboard(
        "催办", "合同", current_user.name,
        contractId=req.contractId, targets=data["notifiedUserIds"],
    )
    return {"code": 0, "data": data, "message": f"已催办 {len(data['notifiedUserIds'])} 位审批人"}


@router.get("/{contract_id}/download", summary="下载合同（PDF 摘要）")
async def download_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    from fastapi.responses import Response
    pdf, fname, content_type = await service.download_contract(db, contract_id)
    await _notify_dashboard("下载", "合同", current_user.name, contractId=contract_id)
    return Response(
        content=pdf,
        media_type=content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{fname}"; filename*=UTF-8\'\'{fname}',
            "Content-Length": str(len(pdf)),
        },
    )
