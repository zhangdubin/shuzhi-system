"""
发票模板路由
- /api/v1/invoice/templates/*
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_permission, CurrentUser
from app.modules.invoice_template import service
from app.modules.invoice_template.schemas import (
    TemplateListRequest, TemplateSave, TemplateDuplicate, TemplateDelete,
)


router = APIRouter()


@router.post("/list", summary="模板列表")
async def list_templates(
    req: TemplateListRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    items, total = await service.list_templates(db, req.page, req.pageSize, req.filters)
    return {"code": 0, "data": {"list": items, "total": total, "page": req.page, "pageSize": req.pageSize}}


@router.post("/detail", summary="模板详情")
async def get_template(
    templateId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.get_template(db, templateId)
    return {"code": 0, "data": data}


@router.post("/save", summary="新建/保存模板")
async def save_template(
    req: TemplateSave,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission("template:write")),
):
    data = await service.save_template(db, req, current_user.id)
    return {"code": 0, "data": data, "message": "保存成功"}


@router.post("/duplicate", summary="复制模板")
async def duplicate_template(
    req: TemplateDuplicate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    data = await service.duplicate_template(db, req.templateId, current_user.id)
    return {"code": 0, "data": data, "message": "已复制"}


@router.post("/delete", summary="删除模板")
async def delete_template(
    req: TemplateDelete,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("template:delete")),
):
    await service.delete_template(db, req.templateId)
    return {"code": 0, "message": "删除成功"}

@router.post("/toggle", summary="启用/停用模板")
async def toggle_template(
    req: TemplateDelete,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.toggle_status(db, req.templateId)
    return {"code": 0, "data": data, "message": data.get("message")}



@router.post("/field-library", summary="可拖拽字段库")
async def field_library(
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.get_field_library(db)
    return {"code": 0, "data": data}
