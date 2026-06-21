"""
发票模板服务层
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException, ParamErrorException, ConflictException
from app.modules.invoice_template.models import InvoiceTemplate, InvoiceTemplateField
from app.modules.invoice_template.schemas import TemplateSave, TemplateField
from app.modules.auth.models import User


def _gen_template_code() -> str:
    return f"TPL-{datetime.now().year}-{uuid.uuid4().hex[:3].upper()}"


# ===== 列表 =====
async def list_templates(
    db: AsyncSession, page: int = 1, page_size: int = 12, filters: dict = None,
) -> tuple[list[dict], int]:
    filters = filters or {}
    query = select(InvoiceTemplate)
    cat = filters.get("category", "all")
    if cat == "created":
        # 我创建的：需要 current_user_id；此处简化用全部（前端会再过滤）
        pass
    elif cat == "market":
        query = query.where(InvoiceTemplate.is_market == True)
    # "all" / "shared"：不过滤

    if filters.get("status"):
        query = query.where(InvoiceTemplate.status == filters["status"])
    if filters.get("type"):
        query = query.where(InvoiceTemplate.category == filters["type"])

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = query.options(
        selectinload(InvoiceTemplate.fields), selectinload(InvoiceTemplate.creator),
    ).order_by(InvoiceTemplate.is_pinned.desc(), InvoiceTemplate.id.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()

    items = []
    for t in rows:
        items.append({
            "id": t.id, "id": t.id, "templateId": t.id, "code": t.code, "name": t.name,
            "description": t.description, "category": t.category,
            "icon": t.icon, "iconColor": (t.icon_colors or "").split(",") if t.icon_colors else [],
            "fieldCount": len(t.fields), "usageCount": t.usage_count,
            "relatedProjectCount": 0,
            "rating": float(t.rating or 5.0),
            "status": t.status, "isPinned": t.is_pinned, "isMarket": t.is_market,
            "creator": {"userId": t.creator.id, "name": t.creator.name, "avatar": t.creator.avatar} if t.creator else None,
            "createdAt": t.created_at, "updatedAt": t.updated_at,
        })
    return items, total


# ===== 详情 =====
async def get_template(db: AsyncSession, template_id: int) -> dict:
    t = (await db.execute(
        select(InvoiceTemplate).where(InvoiceTemplate.id == template_id)
        .options(selectinload(InvoiceTemplate.fields),
                 selectinload(InvoiceTemplate.creator))
    )).scalar_one_or_none()
    if not t:
        raise NotFoundException(f"模板不存在：{template_id}")

    return {
        "id": t.id, "templateId": t.id, "code": t.code, "name": t.name,
        "category": t.category, "description": t.description,
        "defaultTaxRate": float(t.default_tax_rate or 0),
        "status": t.status, "isPinned": t.is_pinned, "isMarket": t.is_market,
        "usageCount": t.usage_count, "rating": float(t.rating or 5.0),
        "icon": t.icon, "iconColor": (t.icon_colors or "").split(",") if t.icon_colors else [],
        "fields": [
            {
                "id": f"f_{f.id}", "label": f.label, "key": f.key, "type": f.type,
                "required": f.is_required,
                "aiExtractEnabled": f.ai_support,    # 前端命名
                "aiSupport": f.ai_support,           # 兼容
                "defaultValue": f.default_value, "linkedField": f.linked_field,
                "refType": f.ref_type, "options": f.options,
                "order": f.seq,                      # 前端用 order 不用 seq
            }
            for f in sorted(t.fields, key=lambda x: x.seq)
        ],
        "creator": {"userId": t.creator.id, "name": t.creator.name, "avatar": t.creator.avatar} if t.creator else None,
        "createdAt": t.created_at, "updatedAt": t.updated_at,
    }


# ===== 保存 =====
async def save_template(db: AsyncSession, req: TemplateSave, creator_id: int) -> dict:
    if req.templateId:
        t = (await db.execute(select(InvoiceTemplate).where(InvoiceTemplate.id == req.templateId))).scalar_one_or_none()
        if not t:
            raise NotFoundException(f"模板不存在：{req.templateId}")
        # 清掉旧 fields
        old_fields = (await db.execute(
            select(InvoiceTemplateField).where(InvoiceTemplateField.template_id == t.id)
        )).scalars().all()
        for f in old_fields:
            await db.delete(f)
    else:
        t = InvoiceTemplate(
            code=req.code or _gen_template_code(),
            name=req.name,
            category=req.category,
            description=req.description,
            default_tax_rate=req.defaultTaxRate,
            icon=req.icon,
            icon_colors=req.iconColors,
            creator_id=creator_id, status="enabled",
        )
        db.add(t)
        await db.flush()
        # 新建后直接跳过下面赋值
    if req.templateId:
        t.name = req.name
        t.category = req.category
        t.description = req.description
        t.default_tax_rate = req.defaultTaxRate
        t.icon = req.icon
        t.icon_colors = req.iconColors

    for seq, f in enumerate(req.fields, start=1):
        db.add(InvoiceTemplateField(
            template_id=t.id, seq=seq, label=f.label, key=f.key, type=f.type,
            is_required=f.required, ai_support=f.aiSupport,
            default_value=str(f.defaultValue) if f.defaultValue is not None else None,
            linked_field=f.linkedField, ref_type=f.refType,
            options=f.options, sort=seq,
        ))
    await db.commit()
    await db.refresh(t)
    return await get_template(db, t.id)


# ===== 复制 =====
async def duplicate_template(db: AsyncSession, template_id: int, creator_id: int) -> dict:
    src = (await db.execute(
        select(InvoiceTemplate).where(InvoiceTemplate.id == template_id)
        .options(selectinload(InvoiceTemplate.fields))
    )).scalar_one_or_none()
    if not src:
        raise NotFoundException(f"模板不存在：{template_id}")

    new = InvoiceTemplate(
        code=_gen_template_code(),
        name=f"{src.name} - 副本",
        category=src.category, description=src.description,
        icon=src.icon, icon_colors=src.icon_colors,
        default_tax_rate=src.default_tax_rate,
        creator_id=creator_id, status="enabled",
    )
    db.add(new)
    await db.flush()
    for f in src.fields:
        db.add(InvoiceTemplateField(
            template_id=new.id, seq=f.seq, label=f.label, key=f.key, type=f.type,
            is_required=f.is_required, ai_support=f.ai_support,
            default_value=f.default_value, linked_field=f.linked_field,
            ref_type=f.ref_type, options=f.options, sort=f.sort,
        ))
    await db.commit()
    await db.refresh(new)
    return await get_template(db, new.id)


# ===== 删除 =====


# ===== 启用/禁用切换 =====
async def toggle_status(db: AsyncSession, template_id: int) -> dict:
    t = (await db.execute(select(InvoiceTemplate).where(InvoiceTemplate.id == template_id))).scalar_one_or_none()
    if not t:
        raise NotFoundException(f"模板不存在：{template_id}")
    t.status = "disabled" if t.status == "enabled" else "enabled"
    await db.commit()
    await db.refresh(t)
    return {"status": t.status, "message": "已启用" if t.status == "enabled" else "已停用"}

async def delete_template(db: AsyncSession, template_id: int):
    t = (await db.execute(select(InvoiceTemplate).where(InvoiceTemplate.id == template_id))).scalar_one_or_none()
    if not t:
        raise NotFoundException(f"模板不存在：{template_id}")
    await db.delete(t)
    await db.commit()


# ===== 字段库（左侧可拖拽） =====
async def get_field_library(db: AsyncSession) -> dict:
    return {
        "groups": [
            {
                "name": "基础信息",
                "fields": [
                    {"label": "发票类型", "key": "invoiceType", "type": "text", "icon": "📄"},
                    {"label": "发票代码", "key": "invoiceCode", "type": "text", "icon": "🔢"},
                    {"label": "发票号码", "key": "invoiceNo", "type": "text", "icon": "#"},
                    {"label": "开票日期", "key": "issueDate", "type": "date", "icon": "📅"},
                ],
            },
            {
                "name": "金额信息",
                "fields": [
                    {"label": "价税合计", "key": "totalAmount", "type": "amount", "icon": "💰"},
                    {"label": "税率", "key": "taxRate", "type": "rate", "icon": "%"},
                    {"label": "税额", "key": "taxAmount", "type": "amount", "icon": "¥"},
                    {"label": "不含税金额", "key": "amountExclTax", "type": "amount", "icon": "💵"},
                ],
            },
            {
                "name": "业务字段",
                "fields": [
                    {"label": "报销人", "key": "reimburserId", "type": "user", "icon": "👤"},
                    {"label": "部门", "key": "departmentId", "type": "text", "icon": "🏢"},
                    {"label": "关联合同", "key": "contractId", "type": "ref", "icon": "📂", "refType": "contract"},
                    {"label": "关联项目", "key": "projectId", "type": "ref", "icon": "📂", "refType": "project"},
                    {"label": "成本中心", "key": "costCenter", "type": "ref", "icon": "📂", "refType": "costCenter"},
                    {"label": "备注", "key": "remark", "type": "textarea", "icon": "📝"},
                ],
            },
        ]
    }
