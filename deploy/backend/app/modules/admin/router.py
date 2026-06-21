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
