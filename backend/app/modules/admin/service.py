"""
管理后台服务层
- 部门 / 角色 / 权限 / 用户 / 字典 / 审计
- R11A：hot data 加 Redis 缓存（depts/permissions/dict）— 写时失效
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import and_, or_, select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.cache import cache, invalidate
from app.core.exceptions import (
    NotFoundException, ParamErrorException, ConflictException,
)
from app.core.security import hash_password
from app.modules.auth.models import (
    Department, Role, Permission, RolePermission, User, UserRole, Dictionary, AuditLog,
)
from app.modules.admin.schemas import (
    DeptCreate, DeptUpdate,
    RoleCreate, RoleUpdate,
    UserCreate, UserUpdate,
    DictCreate, DictUpdate,
)


# ============================================================
# 部门
# ============================================================

async def list_departments(db: AsyncSession, only_active: bool = True) -> tuple[list[dict], int]:
    # R11A 性能优化：hot data Redis 缓存（5 分钟 TTL）
    from app.core.cache import get as cache_get, set_ as cache_set, invalidate as cache_invalidate
    cache_key = f"admin:depts:list:{'active' if only_active else 'all'}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    query = select(Department)
    if only_active:
        query = query.where(Department.is_active == True)
    rows = (await db.execute(
        query.options(selectinload(Department.parent), selectinload(Department.manager))
        .order_by(Department.sort.asc(), Department.id.asc())
    )).scalars().all()

    # 算 memberCount（每个部门的人数）
    counts = dict((await db.execute(
        select(User.department_id, func.count(User.id))
        .where(User.department_id != None, User.is_active == True)
        .group_by(User.department_id)
    )).all())

    items = [
        {
            "id": d.id, "name": d.name, "code": d.code,
            "parentId": d.parent_id, "parentName": d.parent.name if d.parent else None,
            "managerId": d.manager_id, "managerName": d.manager.name if d.manager else None,
            "sort": d.sort, "isActive": d.is_active,
            "memberCount": int(counts.get(d.id, 0)),
            "createdAt": d.created_at,
        }
        for d in rows
    ]
    result = (items, len(items))
    await cache_set(cache_key, result, ttl=300)  # 5 分钟
    return result


async def list_departments_tree(db: AsyncSession) -> list[dict]:
    """
    部门树形结构（前端 GET /admin/depts/tree 用）

    返回：
    [
      {id, name, code, parentId, managerId, managerName, memberCount, isActive, children: [...]}
    ]
    """
    from app.core.cache import get as cache_get, set_ as cache_set
    cache_key = "admin:depts:tree"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    items, _ = await list_departments(db, only_active=True)
    nodes: dict[int, dict] = {it['id']: {**it, 'children': []} for it in items}
    roots: list[dict] = []
    for it in items:
        pid = it.get('parentId')
        if pid and pid in nodes:
            nodes[pid]['children'].append(nodes[it['id']])
        else:
            roots.append(nodes[it['id']])
    await cache_set(cache_key, roots, ttl=300)  # 5 分钟
    return roots


async def create_department(db: AsyncSession, req: DeptCreate) -> dict:
    # 唯一性
    existing = (await db.execute(
        select(Department).where(Department.code == req.code)
    )).scalar_one_or_none()
    if existing:
        raise ConflictException(f"部门代码已存在：{req.code}")
    d = Department(
        name=req.name, code=req.code,
        parent_id=req.parentId, manager_id=req.managerId,
        sort=req.sort, is_active=req.isActive,
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)
    # R11A 失效缓存
    from app.core.cache import invalidate as cache_invalidate
    await cache_invalidate("admin:depts:")
    return {"id": d.id, "name": d.name, "code": d.code, "message": "部门已创建"}


async def update_department(db: AsyncSession, dept_id: int, req: DeptUpdate) -> dict:
    d = (await db.execute(select(Department).where(Department.id == dept_id))).scalar_one_or_none()
    if not d:
        raise NotFoundException(f"部门不存在：{dept_id}")
    # 防自己成自己 parent
    if req.parentId is not None and req.parentId == dept_id:
        raise ParamErrorException("父部门不能是自己")
    data = req.model_dump(exclude_unset=True)
    field_map = {"parentId": "parent_id", "managerId": "manager_id", "isActive": "is_active"}
    for k, v in data.items():
        setattr(d, field_map.get(k, k), v)
    await db.commit()
    # R11A 失效缓存
    from app.core.cache import invalidate as cache_invalidate
    await cache_invalidate("admin:depts:")
    return {"id": d.id, "message": "已更新"}


async def delete_department(db: AsyncSession, dept_id: int) -> dict:
    d = (await db.execute(select(Department).where(Department.id == dept_id))).scalar_one_or_none()
    if not d:
        raise NotFoundException(f"部门不存在：{dept_id}")
    # 防有子部门
    children = (await db.execute(
        select(func.count()).where(Department.parent_id == dept_id)
    )).scalar() or 0
    if children > 0:
        raise ConflictException(f"该部门下有 {children} 个子部门，请先处理")
    # 防有成员
    members = (await db.execute(
        select(func.count()).where(User.department_id == dept_id)
    )).scalar() or 0
    if members > 0:
        raise ConflictException(f"该部门下有 {members} 名成员，请先调岗")
    await db.delete(d)
    await db.commit()
    # R11A 失效缓存
    from app.core.cache import invalidate as cache_invalidate
    await cache_invalidate("admin:depts:")
    return {"id": dept_id, "message": "已删除"}


# ============================================================
# 角色
# ============================================================

async def list_roles(db: AsyncSession) -> tuple[list[dict], int]:
    rows = (await db.execute(
        select(Role).options(selectinload(Role.permissions))
        .order_by(Role.id.asc())
    )).scalars().all()

    # userCount
    counts = dict((await db.execute(
        select(UserRole.role_id, func.count(UserRole.user_id))
        .group_by(UserRole.role_id)
    )).all())

    items = []
    for r in rows:
        items.append({
            "id": r.id, "name": r.name, "code": r.code, "description": r.description,
            "isBuiltin": r.is_builtin, "dataScope": r.data_scope,
            "userCount": int(counts.get(r.id, 0)),
            "permissionCount": len(r.permissions),
            "permissions": [p.code for p in r.permissions],
            "createdAt": r.created_at,
        })
    return items, len(items)


async def get_role(db: AsyncSession, role_id: int) -> dict:
    r = (await db.execute(
        select(Role).where(Role.id == role_id).options(selectinload(Role.permissions))
    )).scalar_one_or_none()
    if not r:
        raise NotFoundException(f"角色不存在：{role_id}")
    return {
        "id": r.id, "name": r.name, "code": r.code, "description": r.description,
        "isBuiltin": r.is_builtin, "dataScope": r.data_scope,
        "userCount": 0, "permissionCount": len(r.permissions),
        "permissions": [p.code for p in r.permissions],
        "createdAt": r.created_at,
    }


async def create_role(db: AsyncSession, req: RoleCreate) -> dict:
    if req.dataScope not in ("all", "dept", "dept_sub", "self", "custom"):
        raise ParamErrorException(f"dataScope 非法：{req.dataScope}")
    existing = (await db.execute(
        select(Role).where(or_(Role.code == req.code, Role.name == req.name))
    )).scalar_one_or_none()
    if existing:
        raise ConflictException("角色 code 或 name 已存在")
    r = Role(name=req.name, code=req.code, description=req.description,
             data_scope=req.dataScope, is_builtin=False)
    db.add(r)
    await db.flush()
    # 关联权限
    if req.permissionCodes:
        perms = (await db.execute(
            select(Permission).where(Permission.code.in_(req.permissionCodes))
        )).scalars().all()
        for p in perms:
            db.add(RolePermission(role_id=r.id, permission_id=p.id))
    await db.commit()
    await db.refresh(r)
    return await get_role(db, r.id)


async def update_role(db: AsyncSession, role_id: int, req: RoleUpdate) -> dict:
    r = (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
    if not r:
        raise NotFoundException(f"角色不存在：{role_id}")
    if r.is_builtin and req.dataScope and req.dataScope != r.data_scope:
        raise ConflictException("内置角色不可修改 dataScope")
    data = req.model_dump(exclude_unset=True)
    if "dataScope" in data:
        if data["dataScope"] not in ("all", "dept", "dept_sub", "self", "custom"):
            raise ParamErrorException(f"dataScope 非法：{data['dataScope']}")
        r.data_scope = data.pop("dataScope")
    if "name" in data:
        r.name = data.pop("name")
    if "description" in data:
        r.description = data.pop("description")
    if "permissionCodes" in data:
        new_codes = set(data.pop("permissionCodes"))
        # 清旧关联
        old = (await db.execute(
            select(RolePermission).where(RolePermission.role_id == role_id)
        )).scalars().all()
        for rp in old:
            await db.delete(rp)
        await db.flush()
        if new_codes:
            perms = (await db.execute(
                select(Permission).where(Permission.code.in_(list(new_codes)))
            )).scalars().all()
            for p in perms:
                db.add(RolePermission(role_id=role_id, permission_id=p.id))
    await db.commit()
    return await get_role(db, role_id)


async def delete_role(db: AsyncSession, role_id: int) -> dict:
    r = (await db.execute(select(Role).where(Role.id == role_id))).scalar_one_or_none()
    if not r:
        raise NotFoundException(f"角色不存在：{role_id}")
    if r.is_builtin:
        raise ConflictException("内置角色不可删除")
    members = (await db.execute(
        select(func.count()).where(UserRole.role_id == role_id)
    )).scalar() or 0
    if members > 0:
        raise ConflictException(f"该角色下有 {members} 名用户，请先解除")
    # 删 role_permission 关联
    rps = (await db.execute(
        select(RolePermission).where(RolePermission.role_id == role_id)
    )).scalars().all()
    for rp in rps:
        await db.delete(rp)
    await db.delete(r)
    await db.commit()
    return {"id": role_id, "message": "已删除"}


# ============================================================
# 权限（只读）
# ============================================================

async def list_permissions(db: AsyncSession) -> tuple[list[dict], int]:
    # R11A 性能优化：hot data Redis 缓存
    from app.core.cache import get as cache_get, set_ as cache_set
    cache_key = "admin:permissions:list"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    rows = (await db.execute(
        select(Permission).order_by(Permission.resource.asc(), Permission.id.asc())
    )).scalars().all()
    items = [
        {
            "id": p.id, "code": p.code, "resource": p.resource, "action": p.action,
            "name": p.name, "description": p.description,
        }
        for p in rows
    ]
    result = (items, len(items))
    await cache_set(cache_key, result, ttl=600)  # 权限点变化少，10 分钟
    return result


# ============================================================
# 用户
# ============================================================

async def list_users(
    db: AsyncSession, page: int = 1, page_size: int = 20,
    keyword: str = "", department_id: Optional[int] = None,
    role_id: Optional[int] = None, is_active: Optional[bool] = None,
) -> tuple[list[dict], int]:
    query = select(User)
    if keyword:
        query = query.where(or_(
            User.name.ilike(f"%{keyword}%"),
            User.username.ilike(f"%{keyword}%"),
            User.email.ilike(f"%{keyword}%"),
            User.phone.ilike(f"%{keyword}%"),
        ))
    if department_id:
        query = query.where(User.department_id == department_id)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    if role_id:
        query = query.join(User.roles).where(Role.id == role_id)

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    query = query.options(
        selectinload(User.department), selectinload(User.roles),
    ).order_by(User.id.asc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(query)).scalars().all()

    # permissionCount 批量
    perm_counts = dict((await db.execute(
        select(UserRole.user_id, func.count(Permission.id))
        .join(Role, Role.id == UserRole.role_id)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .group_by(UserRole.user_id)
    )).all())

    items = []
    for u in rows:
        items.append({
            "id": u.id, "username": u.username, "email": u.email, "phone": u.phone,
            "name": u.name, "avatar": u.avatar,
            "departmentId": u.department_id,
            "departmentName": u.department.name if u.department else None,
            "roleIds": [r.id for r in u.roles],
            "roleNames": [r.name for r in u.roles],
            "roleCodes": [r.code for r in u.roles],
            "permissionCount": int(perm_counts.get(u.id, 0)),
            "isActive": u.is_active, "isAdmin": u.is_admin,
            "lastLoginAt": u.last_login_at, "lastLoginIp": u.last_login_ip,
            "createdAt": u.created_at,
        })
    return items, total


async def get_user(db: AsyncSession, user_id: int) -> dict:
    items, total = await list_users(db, page=1, page_size=1)
    # 简化：实际单独查
    u = (await db.execute(
        select(User).where(User.id == user_id)
        .options(selectinload(User.department), selectinload(User.roles))
    )).scalar_one_or_none()
    if not u:
        raise NotFoundException(f"用户不存在：{user_id}")
    perm_count = (await db.execute(
        select(func.count(Permission.id))
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserRole, UserRole.role_id == Role.id)
        .where(UserRole.user_id == user_id)
    )).scalar() or 0
    return {
        "id": u.id, "username": u.username, "email": u.email, "phone": u.phone,
        "name": u.name, "avatar": u.avatar,
        "departmentId": u.department_id,
        "departmentName": u.department.name if u.department else None,
        "roleIds": [r.id for r in u.roles],
        "roleNames": [r.name for r in u.roles],
        "roleCodes": [r.code for r in u.roles],
        "permissionCount": int(perm_count),
        "isActive": u.is_active, "isAdmin": u.is_admin,
        "lastLoginAt": u.last_login_at, "lastLoginIp": u.last_login_ip,
        "createdAt": u.created_at,
    }


async def create_user(db: AsyncSession, req: UserCreate) -> dict:
    # 兼容前端用 account 字段
    _username = req.get_username()
    if not _username:
        raise ParamErrorException("username / account 必填")
    # 唯一性：仅 username / email 冲突即拒绝（phone 业务上可能换号）
    cond = [User.username == _username]
    if req.email:
        cond.append(User.email == req.email)
    existing = (await db.execute(
        select(User).where(or_(*cond))
    )).scalar_one_or_none()
    if existing:
        raise ConflictException(f"用户名/邮箱已被占用：{_username}")
    u = User(
        username=_username, name=req.name, email=req.email, phone=req.phone,
        avatar=req.avatar, department_id=req.departmentId,
        password_hash=hash_password(req.password),
        is_active=True, is_admin=req.isAdmin,
    )
    db.add(u)
    await db.flush()
    if req.roleIds:
        for rid in req.roleIds:
            db.add(UserRole(user_id=u.id, role_id=rid))
    await db.commit()
    await db.refresh(u)
    return await get_user(db, u.id)


async def update_user(db: AsyncSession, user_id: int, req: UserUpdate) -> dict:
    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not u:
        raise NotFoundException(f"用户不存在：{user_id}")
    data = req.model_dump(exclude_unset=True)
    field_map = {"departmentId": "department_id", "isActive": "is_active", "isAdmin": "is_admin"}
    if "roleIds" in data:
        new_ids = set(data.pop("roleIds"))
        old = (await db.execute(
            select(UserRole).where(UserRole.user_id == user_id)
        )).scalars().all()
        for ur in old:
            await db.delete(ur)
        await db.flush()
        for rid in new_ids:
            db.add(UserRole(user_id=user_id, role_id=rid))
    for k, v in data.items():
        setattr(u, field_map.get(k, k), v)
    await db.commit()
    return await get_user(db, user_id)


async def delete_user(db: AsyncSession, user_id: int) -> dict:
    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not u:
        raise NotFoundException(f"用户不存在：{user_id}")
    if u.is_admin:
        raise ConflictException("不能删除超级管理员")
    # 删 user_role 关联
    urs = (await db.execute(
        select(UserRole).where(UserRole.user_id == user_id)
    )).scalars().all()
    for ur in urs:
        await db.delete(ur)
    await db.delete(u)
    await db.commit()
    return {"id": user_id, "message": "已删除"}

async def batch_delete_users(db: AsyncSession, user_ids: list[int]) -> dict:
    """批量删除用户（不可恢复）。保护规则：超管不能删，删除自己禁止。"""
    if not user_ids:
        raise ParamErrorException("userIds 不能为空")
    rows = (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
    deleted: list[int] = []
    skipped: list[dict] = []
    for u in rows:
        if u.is_admin:
            skipped.append({"id": u.id, "name": u.name, "reason": "超级管理员不可删除"})
            continue
        # 删 user_role 关联
        urs = (await db.execute(select(UserRole).where(UserRole.user_id == u.id))).scalars().all()
        for ur in urs:
            await db.delete(ur)
        await db.delete(u)
        deleted.append(u.id)
    await db.commit()
    return {"deleted": deleted, "skipped": skipped, "deletedCount": len(deleted), "skippedCount": len(skipped)}


async def reset_password(db: AsyncSession, user_id: int, new_password: str) -> dict:
    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not u:
        raise NotFoundException(f"用户不存在：{user_id}")
    u.password_hash = hash_password(new_password)
    await db.commit()
    return {"id": user_id, "message": "密码已重置"}


async def toggle_active(db: AsyncSession, user_id: int, is_active: bool) -> dict:
    u = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not u:
        raise NotFoundException(f"用户不存在：{user_id}")
    if u.is_admin and not is_active:
        raise ConflictException("不能禁用超级管理员")
    u.is_active = is_active
    await db.commit()
    return {"id": user_id, "isActive": u.is_active, "message": "已更新"}


# ============================================================
# 字典
# ============================================================


async def list_dict_types(db: AsyncSession) -> tuple[list[dict], int]:
    """字典分类列表（用 dict_types 表，JOIN dictionaries 统计项数）"""
    from app.modules.auth.models import Dictionary, DictType
    # 项数聚合
    counts = dict((await db.execute(
        select(Dictionary.dict_type, func.count(Dictionary.id))
        .group_by(Dictionary.dict_type)
    )).all())
    active_counts = dict((await db.execute(
        select(Dictionary.dict_type, func.count(Dictionary.id))
        .where(Dictionary.is_active == True)
        .group_by(Dictionary.dict_type)
    )).all())
    types = (await db.execute(
        select(DictType).order_by(DictType.sort.asc(), DictType.id.asc())
    )).scalars().all()
    items = []
    for t in types:
        items.append({
            "id": t.id, "code": t.code, "name": t.name,
            "description": t.description,
            "builtin": t.is_builtin, "sort": t.sort,
            "itemCount": int(counts.get(t.code, 0)),
            "activeCount": int(active_counts.get(t.code, 0)),
        })
    return items, len(items)


async def create_dict_type(db: AsyncSession, code: str, name: str, description: Optional[str] = None) -> dict:
    from app.modules.auth.models import DictType
    existing = (await db.execute(select(DictType).where(DictType.code == code))).scalar_one_or_none()
    if existing:
        raise ConflictException(f"分类 code 已存在：{code}")
    t = DictType(code=code, name=name, description=description, is_builtin=False, sort=99)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return {"id": t.id, "code": t.code, "name": t.name, "builtin": t.is_builtin, "sort": t.sort, "itemCount": 0, "activeCount": 0}


async def update_dict_type(db: AsyncSession, type_id: int, name: Optional[str] = None, description: Optional[str] = None, sort: Optional[int] = None) -> dict:
    from app.modules.auth.models import DictType
    t = (await db.execute(select(DictType).where(DictType.id == type_id))).scalar_one_or_none()
    if not t:
        raise NotFoundException(f"分类不存在：{type_id}")
    if name is not None: t.name = name
    if description is not None: t.description = description
    if sort is not None: t.sort = sort
    await db.commit()
    return {"id": t.id, "code": t.code, "name": t.name}


async def delete_dict_type(db: AsyncSession, type_id: int) -> dict:
    from app.modules.auth.models import DictType, Dictionary
    t = (await db.execute(select(DictType).where(DictType.id == type_id))).scalar_one_or_none()
    if not t:
        raise NotFoundException(f"分类不存在：{type_id}")
    if t.is_builtin:
        raise ConflictException("系统内置分类不可删除")
    # 检查是否还有项
    has_items = (await db.execute(
        select(func.count(Dictionary.id)).where(Dictionary.dict_type == t.code)
    )).scalar() or 0
    if has_items > 0:
        raise ConflictException(f"分类「{t.name}」下还有 {has_items} 个字典项，请先删除字典项")
    await db.delete(t)
    await db.commit()
    return {"id": type_id, "message": "已删除"}


def _dict_type_cn(code: str, fallback: Optional[str] = None) -> str:
    """dictType code → 中文名（前端展示用）"""
    _MAP = {
        "invoice_type": "发票类型",
        "expense_category": "费用类别",
        "project_status": "项目状态",
        "contract_type": "合同类型",
        "approval_status": "审批状态",
        "receivable_status": "回款状态",
        "cost_center": "成本中心",
    }
    return _MAP.get(code) or fallback or code



async def list_dict_by_type(db: AsyncSession, dict_type: str) -> tuple[list[dict], int]:
    # R11A 性能优化：hot data Redis 缓存
    from app.core.cache import get as cache_get, set_ as cache_set
    cache_key = f"admin:dict:{dict_type}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached
    rows = (await db.execute(
        select(Dictionary).where(Dictionary.dict_type == dict_type)
        .order_by(Dictionary.sort.asc(), Dictionary.id.asc())
    )).scalars().all()
    items = [
        {
            "id": d.id, "dictType": d.dict_type, "value": d.value, "label": d.label,
            "color": d.color, "sort": d.sort, "isActive": d.is_active,
            "isBuiltin": d.is_builtin, "description": d.description or "",
        }
        for d in rows
    ]
    result = (items, len(items))
    await cache_set(cache_key, result, ttl=600)  # 字典项变化少，10 分钟
    return result


async def create_dict(db: AsyncSession, req: DictCreate) -> dict:
    existing = (await db.execute(
        select(Dictionary).where(
            Dictionary.dict_type == req.dictType,
            Dictionary.value == req.value,
        )
    )).scalar_one_or_none()
    if existing:
        raise ConflictException(f"字典值已存在：{req.dictType}/{req.value}")
    d = Dictionary(
        dict_type=req.dictType, value=req.value, label=req.label,
        color=req.color, sort=req.sort, is_active=req.isActive,
    )
    db.add(d)
    await db.commit()
    await db.refresh(d)
    # R11A 失效缓存
    from app.core.cache import delete_pattern
    await delete_pattern(f"admin:dict:{req.dictType}*")
    return {"id": d.id, "message": "已创建"}


async def update_dict(db: AsyncSession, dict_id: int, req: DictUpdate) -> dict:
    d = (await db.execute(select(Dictionary).where(Dictionary.id == dict_id))).scalar_one_or_none()
    if not d:
        raise NotFoundException(f"字典项不存在：{dict_id}")
    data = req.model_dump(exclude_unset=True)
    if "isActive" in data:
        d.is_active = data.pop("isActive")
    for k, v in data.items():
        setattr(d, k, v)
    await db.commit()
    # R11A 失效缓存（用 delete_pattern 才能命中 list_dict_by_type 写入的 key）
    from app.core.cache import delete_pattern
    await delete_pattern(f"admin:dict:{d.dict_type}*")
    return {"id": d.id, "message": "已更新"}


async def delete_dict(db: AsyncSession, dict_id: int) -> dict:
    d = (await db.execute(select(Dictionary).where(Dictionary.id == dict_id))).scalar_one_or_none()
    if not d:
        raise NotFoundException(f"字典项不存在：{dict_id}")
    dict_type = d.dict_type
    await db.delete(d)
    await db.commit()
    # R11A 失效缓存
    from app.core.cache import delete_pattern
    await delete_pattern(f"admin:dict:{dict_type}*")
    return {"id": dict_id, "message": "已删除"}


# ============================================================
# 审计日志
# ============================================================

async def list_audit_logs(
    db: AsyncSession, page: int = 1, page_size: int = 20,
    keyword: str = "", filters: dict = None,
) -> tuple[list[dict], int]:
    filters = filters or {}
    query = select(AuditLog)
    if keyword:
        query = query.where(or_(
            AuditLog.operator_name.ilike(f"%{keyword}%"),
            AuditLog.resource_type.ilike(f"%{keyword}%"),
            AuditLog.path.ilike(f"%{keyword}%"),
        ))
    if filters.get("action"):
        query = query.where(AuditLog.action == filters["action"])
    if filters.get("operatorId"):
        query = query.where(AuditLog.operator_id == int(filters["operatorId"]))
    if filters.get("resourceType"):
        query = query.where(AuditLog.resource_type == filters["resourceType"])
    if filters.get("statusCode"):
        query = query.where(AuditLog.status_code == int(filters["statusCode"]))
    dr = filters.get("dateRange")
    if dr and isinstance(dr, list) and len(dr) == 2:
        try:
            d1 = datetime.fromisoformat(dr[0])
            d2 = datetime.fromisoformat(dr[1])
            query = query.where(AuditLog.created_at >= d1, AuditLog.created_at <= d2)
        except Exception:
            pass

    total = (await db.execute(select(func.count()).select_from(query.subquery()))).scalar() or 0
    rows = (await db.execute(
        query.order_by(AuditLog.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()

    items = [
        {
            "id": log.id,
            "operatorId": log.operator_id,
            "operatorName": log.operator_name,
            "action": log.action,
            "resourceType": log.resource_type,
            "resourceId": log.resource_id,
            "resourceCode": log.resource_code,
            "path": log.path,
            "method": log.method,
            "statusCode": log.status_code,
            "ip": log.ip,
            "userAgent": log.user_agent,
            "elapsedMs": log.elapsed_ms,
            "body": (log.body[:200] + "...") if log.body and len(log.body) > 200 else log.body,
            "createdAt": log.created_at,
        }
        for log in rows
    ]
    return items, total
