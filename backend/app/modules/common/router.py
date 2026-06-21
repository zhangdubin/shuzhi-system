"""
公共模块路由
- /api/v1/common/*
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, Request, Body
import json
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
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
@router.post("/clients", summary="客户列表（含档案字段 + 合同聚合）")
async def client_list(
    request: Request,
    keyword: str = "",
    page: int = 1,
    pageSize: int = 50,
    includeInactive: bool = False,
    level: str = "",
    industry: str = "",
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    # 兼容 query / form / JSON body 三种调用
    kw, pg, ps, incl, lvl, ind = keyword, page, pageSize, includeInactive, level, industry
    try:
        body_bytes = await request.body()
        if body_bytes:
            body_json = json.loads(body_bytes)
            if body_json.get("keyword") is not None:
                kw = body_json["keyword"]
            if body_json.get("page") is not None:
                pg = int(body_json["page"])
            if body_json.get("pageSize") is not None:
                ps = int(body_json["pageSize"])
            if body_json.get("includeInactive") is not None:
                incl = bool(body_json["includeInactive"])
            if body_json.get("level") is not None:
                lvl = str(body_json["level"] or "")
            if body_json.get("industry") is not None:
                ind = str(body_json["industry"] or "")
    except Exception:
        pass
    data = await service.list_clients(
        db, kw, pg, ps,
        include_inactive=incl,
        level=lvl.strip().upper() or None,
        industry=ind.strip() or None,
    )
    return {"code": 0, "data": data.model_dump()}


@router.post("/clients/stats", summary="客户统计卡（总数/VIP/活跃/合同金额）")
async def client_stats(
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    return {"code": 0, "data": await service.get_client_stats(db)}


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


def _client_to_dict(c: Client, aggregates: dict | None = None) -> dict:
    """客户转字典；aggregates 为 None 时只返回档案字段（不查合同/项目/应收）

    aggregates 可选键：contracts, projects, receivables, contractAmount, contractCount,
                       planAmount, receivedAmount, pendingAmount
    """
    a = aggregates or {}
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
        # 聚合（仅 detail 用）
        "contractCount": int(a.get("contractCount") or 0),
        "contractAmount": float(a.get("contractAmount") or 0),  # 元
        "projectCount": int(a.get("projectCount") or 0),
        "planAmount": float(a.get("planAmount") or 0),  # 元
        "receivedAmount": float(a.get("receivedAmount") or 0),  # 元
        "pendingAmount": float(a.get("pendingAmount") or 0),  # 元
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
    # 聚合：合同 / 项目 / 应收（仅汇总，列表查子端点）
    aggregates = await _aggregate_client(db, clientId)
    return {"code": 0, "data": _client_to_dict(c, aggregates)}


async def _aggregate_client(db: AsyncSession, client_id: int) -> dict:
    """聚合客户的合同/项目/应收金额统计"""
    from sqlalchemy import func
    from app.modules.contract.models import Contract
    from app.modules.receivable.models import Receivable
    from app.modules.project.models import Project
    from decimal import Decimal

    out: dict = {
        "contractCount": 0, "contractAmount": 0.0,
        "projectCount": 0,
        "planAmount": 0.0, "receivedAmount": 0.0, "pendingAmount": 0.0,
    }
    try:
        c_row = (await db.execute(
            select(func.count(Contract.id), func.coalesce(func.sum(Contract.amount), 0))
            .where(Contract.client_id == client_id)
        )).one()
        out["contractCount"] = int(c_row[0] or 0)
        out["contractAmount"] = float(Decimal(c_row[1] or 0) / 100)
    except Exception:
        pass
    try:
        p_row = (await db.execute(
            select(func.count(Project.id)).where(Project.client_id == client_id)
        )).one()
        out["projectCount"] = int(p_row[0] or 0)
    except Exception:
        pass
    try:
        r_row = (await db.execute(
            select(
                func.coalesce(func.sum(Receivable.plan_amount), 0),
                func.coalesce(func.sum(Receivable.received_amount), 0),
            ).where(Receivable.client_id == client_id)
        )).one()
        plan = Decimal(r_row[0] or 0)
        recv = Decimal(r_row[1] or 0)
        out["planAmount"] = float(plan / 100)
        out["receivedAmount"] = float(recv / 100)
        out["pendingAmount"] = float((plan - recv) / 100)
    except Exception:
        pass
    return out


@router.post("/clients/contracts", summary="客户的合同列表（详情页用）")
async def client_contracts(
    clientId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    from app.modules.contract.models import Contract
    rows = (await db.execute(
        select(Contract).where(Contract.client_id == clientId).order_by(Contract.id.desc()).limit(20)
    )).scalars().all()
    return {"code": 0, "data": [
        {
            "id": c.id, "code": c.code, "name": c.name, "type": c.type,
            "status": c.status, "amount": float((c.amount or 0) / 100),
            "signDate": c.sign_date.isoformat() if c.sign_date else None,
            "expireDate": c.expire_date.isoformat() if c.expire_date else None,
        }
        for c in rows
    ]}


@router.post("/clients/projects", summary="客户的项目列表（详情页用）")
async def client_projects(
    clientId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    from app.modules.project.models import Project
    rows = (await db.execute(
        select(Project).where(Project.client_id == clientId).order_by(Project.id.desc()).limit(20)
    )).scalars().all()
    return {"code": 0, "data": [
        {
            "id": p.id, "code": p.code, "name": p.name, "status": p.status,
            "progress": float(p.progress or 0),
            "startDate": p.start_date.isoformat() if p.start_date else None,
            "endDate": p.end_date.isoformat() if p.end_date else None,
        }
        for p in rows
    ]}


@router.post("/clients/receivables", summary="客户的回款列表（详情页用）")
async def client_receivables(
    clientId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    from app.modules.receivable.models import Receivable
    rows = (await db.execute(
        select(Receivable).where(Receivable.client_id == clientId).order_by(Receivable.id.desc()).limit(20)
    )).scalars().all()
    return {"code": 0, "data": [
        {
            "id": r.id, "code": r.code, "contractId": r.contract_id,
            "type": r.type, "status": r.status,
            "planAmount": float((r.plan_amount or 0) / 100),
            "receivedAmount": float((r.received_amount or 0) / 100),
            "planDate": r.plan_date.isoformat() if r.plan_date else None,
            "actualDate": r.actual_date.isoformat() if r.actual_date else None,
            "overdueDays": r.overdue_days or 0,
        }
        for r in rows
    ]}


@router.post("/clients/dup-check", summary="客户查重（按名称/税号模糊匹配）")
async def client_dup_check(
    request: Request,
    name: str = "",
    taxNo: str = "",
    excludeId: int | None = None,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    """实时查重：按 name ILIKE 或 taxNo 精确匹配；默认包含已停用客户（避免同名复用）

    - 至少需要一个非空字段；否则返回空（前端空字符串不查）
    - excludeId 编辑时排除自身
    - 最多返回 5 条，按更新时间倒序
    """
    from sqlalchemy import or_

    body_name, body_tax, body_exclude = name, taxNo, excludeId
    try:
        body_bytes = await request.body()
        if body_bytes:
            body_json = json.loads(body_bytes)
            if body_json.get("name") is not None:
                body_name = str(body_json["name"] or "")
            if body_json.get("taxNo") is not None:
                body_tax = str(body_json["taxNo"] or "")
            if body_json.get("excludeId") is not None:
                body_exclude = body_json["excludeId"]
    except Exception:
        pass

    body_name = (body_name or "").strip()
    body_tax = (body_tax or "").strip()
    if not body_name and not body_tax:
        return {"code": 0, "data": {"matches": [], "total": 0}}

    conds = []
    if body_name:
        conds.append(Client.name.ilike(f"%{body_name}%"))
        conds.append(Client.short_name.ilike(f"%{body_name}%"))
    if body_tax:
        conds.append(Client.tax_no == body_tax)
    query = select(Client).where(or_(*conds))
    if body_exclude is not None:
        query = query.where(Client.id != int(body_exclude))
    query = query.order_by(Client.updated_at.desc().nulls_last(), Client.id.desc()).limit(5)
    rows = (await db.execute(query)).scalars().all()
    items = [
        {
            "id": c.id,
            "name": c.name,
            "shortName": c.short_name,
            "taxNo": c.tax_no,
            "level": c.level or "D",
            "isActive": bool(c.is_active),
            "createdAt": c.created_at.isoformat() if c.created_at else None,
        }
        for c in rows
    ]
    return {"code": 0, "data": {"matches": items, "total": len(items)}}


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


# ===== 文件库（专门管理非结构化数据：发票 PDF/图片/合同附件/报销凭证）=====
@router.post("/files/list", summary="文件库列表（按业务/类型/存储过滤）")
async def list_files(
    body: dict | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    """支持 query ?bizType=&bizId=&storage=&keyword= 或 body 传"""
    from sqlalchemy import select, func, or_
    from app.modules.common.models import File as FileModel
    biz_type = (body or {}).get("bizType") or None
    biz_id = (body or {}).get("bizId")
    storage = (body or {}).get("storage") or None
    keyword = (body or {}).get("keyword") or ""
    page = int((body or {}).get("page", 1))
    page_size = min(int((body or {}).get("pageSize", 50)), 200)
    query = select(FileModel)
    if biz_type:
        query = query.where(FileModel.biz_type == biz_type)
    if biz_id is not None:
        query = query.where(FileModel.biz_id == int(biz_id))
    if storage:
        query = query.where(FileModel.storage == storage)
    if keyword:
        query = query.where(or_(FileModel.name.ilike(f"%{keyword}%"), FileModel.id.ilike(f"%{keyword}%")))
    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    rows = (await db.execute(
        query.order_by(FileModel.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    # JOIN users 拿 uploaderName
    from app.modules.auth.models import User as UserModel
    uids = {r.uploader_id for r in rows if r.uploader_id}
    u_map: dict[int, str] = {}
    if uids:
        for u in (await db.execute(select(UserModel.id, UserModel.name, UserModel.username).where(UserModel.id.in_(uids)))).all():
            u_map[u[0]] = u[1] or u[2] or str(u[0])
    return {
        "code": 0,
        "data": {
            "list": [
                {
                    "fileId": r.id,
                    "name": r.name,
                    "ext": r.ext or "",
                    "size": r.size or 0,
                    "mimeType": r.mime_type or "",
                    "url": r.url,
                    "storage": r.storage or "local",
                    "uploaderId": r.uploader_id,
                    "uploaderName": u_map.get(r.uploader_id, "—"),
                    "bizType": r.biz_type,
                    "bizId": r.biz_id,
                    "createdAt": r.created_at.isoformat() if r.created_at else None,
                } for r in rows
            ],
            "total": total,
            "page": page,
            "pageSize": page_size,
        },
    }


@router.post("/files/stats", summary="文件库统计")
async def files_stats(
    body: dict | None = Body(default=None),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    """返回：总数 / 按 storage 分布 / 按 biz_type 分布 / 总大小 / 最近 7 天上传数"""
    from sqlalchemy import select, func, func
    from app.modules.common.models import File as FileModel
    biz_type = (body or {}).get("bizType") or None
    total = (await db.execute(select(func.count(FileModel.id)).where(FileModel.biz_type == biz_type) if biz_type else select(func.count(FileModel.id)))).scalar() or 0
    total_size = (await db.execute(select(func.coalesce(func.sum(FileModel.size), 0)).where(FileModel.biz_type == biz_type) if biz_type else select(func.coalesce(func.sum(FileModel.size), 0)))).scalar() or 0
    # 按 storage 分组
    by_storage = {}
    for r in (await db.execute(
        select(FileModel.storage, func.count(FileModel.id), func.coalesce(func.sum(FileModel.size), 0))
        .where(FileModel.biz_type == biz_type) if biz_type else
        select(FileModel.storage, func.count(FileModel.id), func.coalesce(func.sum(FileModel.size), 0))
        .group_by(FileModel.storage)
    )).all():
        by_storage[r[0] or "local"] = {"count": r[1], "size": int(r[2] or 0)}
    # 按 biz_type 分组
    by_biz = {}
    if not biz_type:
        for r in (await db.execute(
            select(FileModel.biz_type, func.count(FileModel.id), func.coalesce(func.sum(FileModel.size), 0))
            .group_by(FileModel.biz_type)
        )).all():
            by_biz[r[0] or "unknown"] = {"count": r[1], "size": int(r[2] or 0)}
    return {
        "code": 0,
        "data": {
            "total": total,
            "totalSize": int(total_size),
            "byStorage": by_storage,
            "byBizType": by_biz,
        },
    }
