"""
管理后台路由
- /api/v1/admin/*
- 子模块：depts / roles / perms / users / dicts / audit-logs

所有写接口要求 user:write / role:write / dept:write / dict:write 权限
（见 BACKEND.md §6.3 权限 code 清单）
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, require_permission, CurrentUser
from app.modules.admin import service
from app.modules.admin import schemas as sch


router = APIRouter()


# ============================================================
# 部门
# ============================================================

@router.post("/depts/list", summary="部门列表（平铺）")
async def depts_list(
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("dept:read")),
):
    items, total = await service.list_departments(db)
    return {"code": 0, "data": {"list": items, "total": total}}


@router.get("/depts/tree", summary="部门树（前端 AdminDept 用）")
async def depts_tree(
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(get_current_user),
):
    """部门树形结构（GET 调用，返回含 children 的树）"""
    items = await service.list_departments_tree(db)
    return {"code": 0, "data": {"list": items, "total": len(items)}}


@router.post("/depts/create", summary="创建部门")
async def depts_create(
    req: sch.DeptCreate,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("dept:write")),
):
    data = await service.create_department(db, req)
    return {"code": 0, "data": data, "message": "部门已创建"}


@router.post("/depts/update", summary="更新部门")
async def depts_update(
    deptId: int = Query(...),
    req: sch.DeptUpdate = ...,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("dept:write")),
):
    data = await service.update_department(db, deptId, req)
    return {"code": 0, "data": data, "message": "已更新"}


@router.post("/depts/delete", summary="删除部门")
async def depts_delete(
    deptId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("dept:write")),
):
    data = await service.delete_department(db, deptId)
    return {"code": 0, "data": data, "message": "已删除"}


# ============================================================
# 角色
# ============================================================

@router.post("/roles/list", summary="角色列表")
async def roles_list(
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("role:read")),
):
    items, total = await service.list_roles(db)
    return {"code": 0, "data": {"list": items, "total": total}}


@router.post("/roles/detail", summary="角色详情")
async def roles_detail(
    roleId: int = Query(..., description="角色 ID"),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("role:read")),
):
    data = await service.get_role(db, roleId)
    return {"code": 0, "data": data}


@router.post("/roles/create", summary="创建角色")
async def roles_create(
    req: sch.RoleCreate,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("role:write")),
):
    data = await service.create_role(db, req)
    return {"code": 0, "data": data, "message": "角色已创建"}


@router.post("/roles/update", summary="更新角色（含分配权限）")
async def roles_update(
    roleId: int = Query(...),
    req: sch.RoleUpdate = ...,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("role:write")),
):
    data = await service.update_role(db, roleId, req)
    return {"code": 0, "data": data, "message": "已更新"}


@router.post("/roles/delete", summary="删除角色")
async def roles_delete(
    roleId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("role:write")),
):
    data = await service.delete_role(db, roleId)
    return {"code": 0, "data": data, "message": "已删除"}


# ============================================================
# 权限（只读）
# ============================================================

@router.post("/permissions/list", summary="权限点全量列表")
async def perms_list(
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("user:read")),
):
    items, total = await service.list_permissions(db)
    return {"code": 0, "data": {"list": items, "total": total}}


# ============================================================
# 用户
# ============================================================

@router.post("/users/list", summary="用户列表")
async def users_list(
    req: sch.UserListRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("user:read")),
):
    items, total = await service.list_users(
        db, req.page, req.pageSize, req.keyword,
        req.departmentId, req.roleId, req.isActive,
    )
    return {"code": 0, "data": {"list": items, "total": total, "page": req.page, "pageSize": req.pageSize}}


@router.post("/users/detail", summary="用户详情")
async def users_detail(
    userId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("user:read")),
):
    data = await service.get_user(db, userId)
    return {"code": 0, "data": data}


@router.post("/users/create", summary="创建用户")
async def users_create(
    req: sch.UserCreate,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("user:write")),
):
    data = await service.create_user(db, req)
    return {"code": 0, "data": data, "message": "用户已创建"}


@router.post("/users/update", summary="更新用户")
async def users_update(
    userId: int = Query(...),
    req: sch.UserUpdate = ...,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("user:write")),
):
    data = await service.update_user(db, userId, req)
    return {"code": 0, "data": data, "message": "已更新"}


@router.post("/users/delete", summary="删除用户")
async def users_delete(
    userId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("user:write")),
):
    data = await service.delete_user(db, userId)
    return {"code": 0, "data": data, "message": "已删除"}


@router.post("/users/batch-delete", summary="批量删除用户")
async def users_batch_delete(
    req: sch.UserBatchDelete,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("user:write")),
):
    data = await service.batch_delete_users(db, req.userIds)
    msg = f"已删除 {data['deletedCount']} 个用户"
    if data.get("skipped"):
        msg += f"，跳过 {data['skippedCount']} 个（超级管理员）"
    return {"code": 0, "data": data, "message": msg}


@router.post("/users/reset-password", summary="重置密码")
async def users_reset_password(
    req: sch.UserResetPassword,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("user:write")),
):
    data = await service.reset_password(db, req.userId, req.newPassword)
    return {"code": 0, "data": data, "message": "密码已重置"}


@router.post("/users/toggle-active", summary="启用/禁用用户")
async def users_toggle_active(
    req: sch.UserToggleActive,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("user:write")),
):
    data = await service.toggle_active(db, req.userId, req.isActive)
    return {"code": 0, "data": data, "message": "已更新"}


# ============================================================
# 字典
# ============================================================

@router.get("/dicts/types", summary="字典分类列表（dictType 列表 + 各分类的项数）")
async def dicts_types(
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("dict:read")),
):
    items, total = await service.list_dict_types(db)
    return {"code": 0, "data": {"list": items, "total": total}}


@router.post("/dicts/types/create", summary="新建字典分类")
async def dicts_types_create(
    req: sch.DictTypeCreate,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("dict:write")),
):
    data = await service.create_dict_type(db, req.code, req.name, req.description)
    return {"code": 0, "data": data, "message": "已创建"}


@router.post("/dicts/types/update", summary="更新字典分类")
async def dicts_types_update(
    req: sch.DictTypeUpdate,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("dict:write")),
):
    data = await service.update_dict_type(db, req.id, req.name, req.description, req.sort)
    return {"code": 0, "data": data, "message": "已更新"}


@router.post("/dicts/types/delete", summary="删除字典分类")
async def dicts_types_delete(
    id: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("dict:write")),
):
    data = await service.delete_dict_type(db, id)
    return {"code": 0, "data": data, "message": "已删除"}


@router.post("/dicts/list", summary="字典项列表（按 dictType）")
async def dicts_list(
    dictType: str = Query(..., description="字典类型，如 expense_category"),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("dict:read")),
):
    items, total = await service.list_dict_by_type(db, dictType)
    return {"code": 0, "data": {"list": items, "total": total}}


@router.post("/dicts/create", summary="新增字典项")
async def dicts_create(
    req: sch.DictCreate,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("dict:write")),
):
    data = await service.create_dict(db, req)
    return {"code": 0, "data": data, "message": "已创建"}


@router.post("/dicts/update", summary="更新字典项")
async def dicts_update(
    dictId: int = Query(...),
    req: sch.DictUpdate = ...,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("dict:write")),
):
    data = await service.update_dict(db, dictId, req)
    return {"code": 0, "data": data, "message": "已更新"}


@router.post("/dicts/delete", summary="删除字典项")
async def dicts_delete(
    dictId: int = Query(...),
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("dict:write")),
):
    data = await service.delete_dict(db, dictId)
    return {"code": 0, "data": data, "message": "已删除"}


@router.post("/dicts/invalidate-cache", summary="失效字典 Redis 缓存（同步到所有下拉）")
async def dicts_invalidate_cache(
    dictType: Optional[str] = None,
    _user: CurrentUser = Depends(get_current_user),
):
    """失效字典缓存：
    - 不传 dictType：失效所有 admin:dict:* 键
    - 传 dictType：只失效该分类
    """
    from app.core.cache import delete_pattern
    pattern = f"admin:dict:{dictType}*" if dictType else "admin:dict:*"
    n = await delete_pattern(pattern)
    return {"code": 0, "data": {"invalidated": n, "pattern": pattern}, "message": f"已失效 {n} 个缓存键"}


# ============================================================
# 审计日志
# ============================================================

@router.post("/audit-logs/list", summary="审计日志列表")
async def audit_logs_list(
    req: sch.AuditLogListRequest,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("audit:read")),
):
    items, total = await service.list_audit_logs(
        db, req.page, req.pageSize, req.keyword, req.filters,
    )
    return {"code": 0, "data": {"list": items, "total": total, "page": req.page, "pageSize": req.pageSize}}



# ============================================================
# 审批流模板（超管配置）
# ============================================================

@router.get("/approval-templates/list", summary="审批流模板列表")
async def approval_templates_list(
    business_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("admin:approval:read")),
):
    """列出所有审批流模板（按 business_type 可过滤）"""
    from app.modules.common.models import ApprovalTemplate
    from sqlalchemy import select
    q = select(ApprovalTemplate).order_by(ApprovalTemplate.business_type.asc(), ApprovalTemplate.sort_order.asc(), ApprovalTemplate.id.asc())
    if business_type:
        q = q.where(ApprovalTemplate.business_type == business_type)
    rows = (await db.execute(q)).scalars().all()
    return {
        "code": 0,
        "data": [
            {
                "id": t.id,
                "name": t.name,
                "businessType": t.business_type,
                "rules": t.rules or [],
                "condition": t.condition or {},
                "isDefault": t.is_default,
                "isActive": t.is_active,
                "sortOrder": t.sort_order,
                "remark": t.remark or "",
                "createdAt": t.created_at.isoformat() if t.created_at else None,
                "updatedAt": t.updated_at.isoformat() if t.updated_at else None,
            }
            for t in rows
        ],
    }


@router.post("/approval-templates/create", summary="新建审批流模板")
async def approval_templates_create(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("admin:approval:write")),
):
    from app.modules.common.models import ApprovalTemplate
    from sqlalchemy import select
    name = (payload.get("name") or "").strip()
    business_type = (payload.get("businessType") or "expense").strip()
    rules = payload.get("rules") or []
    if not name:
        from app.core.exceptions import ParamErrorException
        raise ParamErrorException("模板名称不能为空")
    if not isinstance(rules, list) or len(rules) == 0:
        from app.core.exceptions import ParamErrorException
        raise ParamErrorException("至少需要 1 个审批步骤")
    is_default = bool(payload.get("isDefault"))
    # 如果设为默认，先把同 business_type 其他默认取消
    if is_default:
        existing = (await db.execute(select(ApprovalTemplate).where(
            ApprovalTemplate.business_type == business_type,
            ApprovalTemplate.is_default == True  # noqa: E712
        ))).scalars().all()
        for t in existing:
            t.is_default = False
    t = ApprovalTemplate(
        name=name,
        business_type=business_type,
        rules=rules,
        condition=payload.get("condition") or None,
        is_default=is_default,
        is_active=bool(payload.get("isActive", True)),
        sort_order=int(payload.get("sortOrder") or 0),
        remark=payload.get("remark") or None,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return {"code": 0, "data": {"id": t.id}}


@router.post("/approval-templates/update", summary="更新审批流模板")
async def approval_templates_update(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("admin:approval:write")),
):
    from app.modules.common.models import ApprovalTemplate
    from sqlalchemy import select
    tid = int(payload.get("id") or 0)
    if not tid:
        from app.core.exceptions import ParamErrorException
        raise ParamErrorException("缺少 id")
    t = (await db.execute(select(ApprovalTemplate).where(ApprovalTemplate.id == tid))).scalar_one_or_none()
    if not t:
        from app.core.exceptions import NotFoundException
        raise NotFoundException(f"模板不存在：{tid}")
    if "name" in payload: t.name = (payload.get("name") or "").strip()
    if "rules" in payload:
        rules = payload.get("rules") or []
        if not isinstance(rules, list) or len(rules) == 0:
            from app.core.exceptions import ParamErrorException
            raise ParamErrorException("至少需要 1 个审批步骤")
        t.rules = rules
    if "condition" in payload: t.condition = payload.get("condition") or None
    if "isActive" in payload: t.is_active = bool(payload.get("isActive"))
    if "sortOrder" in payload: t.sort_order = int(payload.get("sortOrder") or 0)
    if "remark" in payload: t.remark = payload.get("remark") or None
    if "isDefault" in payload:
        new_default = bool(payload.get("isDefault"))
        if new_default:
            # 把同 business_type 其他默认取消
            existing = (await db.execute(select(ApprovalTemplate).where(
                ApprovalTemplate.business_type == t.business_type,
                ApprovalTemplate.is_default == True,  # noqa: E712
                ApprovalTemplate.id != t.id,
            ))).scalars().all()
            for x in existing:
                x.is_default = False
        t.is_default = new_default
    await db.commit()
    return {"code": 0, "data": {"id": t.id}}


@router.post("/approval-templates/delete", summary="删除审批流模板")
async def approval_templates_delete(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("admin:approval:write")),
):
    from app.modules.common.models import ApprovalTemplate
    from sqlalchemy import select
    tid = int(payload.get("id") or 0)
    if not tid:
        from app.core.exceptions import ParamErrorException
        raise ParamErrorException("缺少 id")
    t = (await db.execute(select(ApprovalTemplate).where(ApprovalTemplate.id == tid))).scalar_one_or_none()
    if not t:
        from app.core.exceptions import NotFoundException
        raise NotFoundException(f"模板不存在：{tid}")
    await db.delete(t)
    await db.commit()
    return {"code": 0, "data": {"id": tid}}


@router.post("/approval-templates/seed-defaults", summary="一键初始化默认模板（业务类型 → 3 步标准流）")
async def approval_templates_seed_defaults(
    db: AsyncSession = Depends(get_db),
    _user: CurrentUser = Depends(require_permission("admin:approval:write")),
):
    """给常用业务类型插入默认模板（如果还没有任何模板的话）"""
    from app.modules.common.models import ApprovalTemplate
    from sqlalchemy import select, func
    defaults = [
        {"name": "标准审批流", "business_type": "expense",   "rules": ["submitter", "direct_leader", "finance"], "condition": None,            "is_default": True},
        {"name": "大额审批流", "business_type": "expense",   "rules": ["submitter", "direct_leader", "finance", "gm_if_over_5000"], "condition": {"amount_min": 500000}, "is_default": False},
    ]
    inserted = []
    for d in defaults:
        # 已存在同名模板则跳过
        exist = (await db.execute(select(func.count(ApprovalTemplate.id)).where(
            ApprovalTemplate.business_type == d["business_type"],
            ApprovalTemplate.name == d["name"],
        ))).scalar()
        if exist:
            continue
        t = ApprovalTemplate(
            name=d["name"],
            business_type=d["business_type"],
            rules=d["rules"],
            condition=d["condition"],
            is_default=d["is_default"],
            is_active=True,
            sort_order=0,
            remark="系统初始化",
        )
        db.add(t)
        inserted.append(d["name"])
    await db.commit()
    return {"code": 0, "data": {"inserted": inserted}}
