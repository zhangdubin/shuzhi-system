"""
公共模块路由
- /api/v1/common/*
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, Request
import json
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import random
import string

from app.core.database import get_db
from app.core.security import get_current_user, CurrentUser
from app.core.exceptions import ConflictException, NotFoundException, ParamErrorException
from app.modules.common import service
from app.modules.common.models import Client


router = APIRouter()


# ===== 字典 =====
@router.get("/dict", summary="通用字典（query 参数，前端默认调用）")
async def dict_list(
    dictType: str = Query(..., description="字典类型"),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.list_dict(db, dictType)
    return {"code": 0, "data": data.model_dump()}


class DictQuery(BaseModel):
    dictType: str


@router.post("/dict", summary="通用字典（兼容 form 和 JSON body）")
async def dict_list_form(
    request: Request,
    dictType: str = Form(None, description="字典类型（form）"),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    # 兼容 form / JSON body 两种调用
    dt = dictType
    if not dt:
        try:
            body_bytes = await request.body()
            if body_bytes:
                body_json = json.loads(body_bytes)
                dt = body_json.get("dictType")
        except Exception:
            pass
    if not dt:
        raise ParamErrorException("dictType 必填")
    data = await service.list_dict(db, dt)
    return {"code": 0, "data": data.model_dump()}


# ===== 用户引用 =====
@router.post("/users", summary="用户列表（用于下拉选择）")
async def user_list(
    keyword: str = "",
    departmentId: int | None = None,
    page: int = 1,
    pageSize: int = 50,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.list_users(db, keyword, departmentId, page, pageSize)
    return {"code": 0, "data": data.model_dump()}


# ===== 客户引用 =====
@router.post("/clients", summary="客户列表")
async def client_list(
    keyword: str = "",
    page: int = 1,
    pageSize: int = 50,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    data = await service.list_clients(db, keyword, page, pageSize)
    return {"code": 0, "data": data.model_dump()}


# ===== 客户 CRUD =====
class ClientCreateReq(BaseModel):
    name: str
    code: str | None = None
    shortName: str | None = None
    taxNo: str | None = None
    legalPerson: str | None = None
    contactName: str | None = None
    contactPhone: str | None = None
    contactEmail: str | None = None
    address: str | None = None
    bankName: str | None = None
    bankAccount: str | None = None
    industry: str | None = None
    level: str = "C"
    remark: str | None = None


class ClientUpdateReq(BaseModel):
    name: str | None = None
    shortName: str | None = None
    taxNo: str | None = None
    legalPerson: str | None = None
    contactName: str | None = None
    contactPhone: str | None = None
    contactEmail: str | None = None
    address: str | None = None
    bankName: str | None = None
    bankAccount: str | None = None
    industry: str | None = None
    level: str | None = None
    isActive: bool | None = None
    remark: str | None = None


def _gen_client_code() -> str:
    """生成唯一客户编号（CL-YYYY-NNNNXX）"""
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"CL-{datetime.utcnow().year}-{suffix}"


def _client_to_dict(c: Client) -> dict:
    return {
        "id": c.id,
        "code": c.code,
        "name": c.name,
        "shortName": c.short_name,
        "taxNo": c.tax_no,
        "legalPerson": c.legal_person,
        "contactName": c.contact_name,
        "contactPhone": c.contact_phone,
        "contactEmail": c.contact_email,
        "address": c.address,
        "bankName": c.bank_name,
        "bankAccount": c.bank_account,
        "industry": c.industry,
        "level": c.level,
        "isActive": c.is_active,
        "remark": c.remark,
        "createdAt": c.created_at.isoformat() if c.created_at else None,
    }


@router.post("/clients/create", summary="创建客户")
async def client_create(
    req: ClientCreateReq,
    db: AsyncSession = Depends(get_db),
    user: CurrentUser = Depends(get_current_user),
):
    """创建客户（前端 ClientCreate 用）"""
    code = req.code or _gen_client_code()
    c = Client(
        code=code,
        name=req.name,
        short_name=req.shortName,
        tax_no=req.taxNo,
        legal_person=req.legalPerson,
        contact_name=req.contactName,
        contact_phone=req.contactPhone,
        contact_email=req.contactEmail,
        address=req.address,
        bank_name=req.bankName,
        bank_account=req.bankAccount,
        industry=req.industry,
        level=req.level,
        remark=req.remark,
        created_by=user.id,
    )
    db.add(c)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        # 唯一冲突（code 已存在 / name+taxNo 唯一约束）
        if "unique" in str(e.orig).lower() or "duplicate" in str(e.orig).lower():
            raise ConflictException(
                f"客户编号「{code}」已存在，请修改后重试" if req.code
                else "客户信息重复（可能纳税人识别号已登记）"
            )
        raise
    await db.refresh(c)
    return {"code": 0, "data": _client_to_dict(c), "message": "客户已创建"}


@router.post("/clients/detail", summary="客户详情")
async def client_detail(
    clientId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    c = (await db.execute(select(Client).where(Client.id == clientId))).scalar_one_or_none()
    if not c:
        return {"code": 404, "message": "客户不存在"}
    return {"code": 0, "data": _client_to_dict(c)}


@router.post("/clients/update", summary="更新客户")
async def client_update(
    clientId: int = Query(...),
    req: ClientUpdateReq = ...,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    c = (await db.execute(select(Client).where(Client.id == clientId))).scalar_one_or_none()
    if not c:
        return {"code": 404, "message": "客户不存在"}
    field_map = {
        "name": "name", "shortName": "short_name", "taxNo": "tax_no",
        "legalPerson": "legal_person", "contactName": "contact_name",
        "contactPhone": "contact_phone", "contactEmail": "contact_email",
        "address": "address", "bankName": "bank_name", "bankAccount": "bank_account",
        "industry": "industry", "level": "level", "isActive": "is_active",
        "remark": "remark",
    }
    for k, v in req.model_dump(exclude_unset=True).items():
        if k in field_map and v is not None:
            setattr(c, field_map[k], v)
    await db.commit()
    await db.refresh(c)
    return {"code": 0, "data": _client_to_dict(c), "message": "已更新"}


@router.post("/clients/delete", summary="删除客户（软删除）")
async def client_delete(
    clientId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    c = (await db.execute(select(Client).where(Client.id == clientId))).scalar_one_or_none()
    if not c:
        return {"code": 404, "message": "客户不存在"}
    c.is_active = False
    await db.commit()
    return {"code": 0, "data": {"deleted": True}, "message": "已删除"}


# ===== 合同/项目引用 =====
@router.post("/contracts/ref", summary="合同引用（按客户过滤）")
async def contract_ref(
    clientId: int | None = None,
    keyword: str = "",
    page: int = 1,
    pageSize: int = 20,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    items = await service.list_contracts_ref(db, clientId, keyword, page, pageSize)
    return {"code": 0, "data": {"list": [i.model_dump() for i in items]}}


@router.post("/projects/ref", summary="项目引用（按客户过滤）")
async def project_ref(
    clientId: int | None = None,
    keyword: str = "",
    page: int = 1,
    pageSize: int = 20,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    items = await service.list_projects_ref(db, clientId, keyword, page, pageSize)
    return {"code": 0, "data": {"list": [i.model_dump() for i in items]}}


# ===== 文件上传 =====
@router.post("/upload", summary="通用文件上传")
async def upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    info = await service.save_upload_file(db, current_user.id, file)
    return {"code": 0, "data": info.model_dump()}
