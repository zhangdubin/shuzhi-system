"""
R11B 权限细化：data_scope 数据范围过滤 helper
- all: 不过滤
- dept_sub: 当前部门 + 所有子部门（含子部门子部门）
- dept: 仅当前部门
- self: 仅 created_by/applicant_id = current_user.id
- custom: 同 dept（5 档最严格）
"""
import logging
from typing import Optional, Sequence

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from app.core.cache import get as cache_get, set_ as cache_set
from app.core.security import CurrentUser

logger = logging.getLogger(__name__)

DATA_SCOPE_ALL = "all"
DATA_SCOPE_DEPT_SUB = "dept_sub"
DATA_SCOPE_DEPT = "dept"
DATA_SCOPE_SELF = "self"
DATA_SCOPE_CUSTOM = "custom"


async def get_dept_subtree_ids(db: AsyncSession, dept_id: int) -> list[int]:
    """
    递归获取部门子树所有 dept_id（含自身）
    - 5 分钟 Redis 缓存（部门树变化少）
    """
    from app.modules.auth.models import Department
    cache_key = f"data_scope:dept_subtree:{dept_id}"
    cached = await cache_get(cache_key)
    if cached is not None:
        return cached

    # 一次 SQL 拉所有部门，内存递归
    rows = (await db.execute(
        select(Department.id, Department.parent_id)
    )).all()
    children_map: dict[Optional[int], list[int]] = {}
    for r in rows:
        children_map.setdefault(r.parent_id, []).append(r.id)

    result: list[int] = []
    stack = [dept_id]
    while stack:
        cur = stack.pop()
        if cur in result:
            continue
        result.append(cur)
        for child in children_map.get(cur, []):
            stack.append(child)

    await cache_set(cache_key, result, ttl=300)  # 5 分钟
    return result


def build_data_scope_filter(
    query,
    model,
    current_user: CurrentUser,
    *,
    owner_field: Optional[InstrumentedAttribute] = None,
    direct_dept_field: Optional[InstrumentedAttribute] = None,
    owner_via_user_dept: bool = False,
):
    """
    在 SQLAlchemy query 上追加 data_scope 过滤条件
    - is_admin / data_scope='all' 不过滤
    - data_scope='dept_sub': direct_dept_field IN (dept_subtree) OR owner_field IN (dept_subtree users)
    - data_scope='dept': direct_dept_field = current_user.department_id
    - data_scope='self': owner_field = current_user.id
    - data_scope='custom': 同 dept

    Args:
        query: 已构造的 select query
        model: ORM 模型
        current_user: CurrentUser
        owner_field: 创建者字段（如 Contract.manager_id, Expense.applicant_id）
        direct_dept_field: 直接 dept_id 字段（如 Expense.department_id）
        owner_via_user_dept: owner_field 关联 user.department_id（间接部门过滤）

    Returns:
        加过滤后的 query
    """
    if current_user.is_admin or current_user.data_scope == DATA_SCOPE_ALL:
        return query  # 不加过滤

    scope = current_user.data_scope
    user_dept_id = current_user.department_id

    if scope in (DATA_SCOPE_DEPT, DATA_SCOPE_CUSTOM):
        # 仅当前部门
        if direct_dept_field is not None:
            return query.where(direct_dept_field == user_dept_id)
        if owner_field is not None and owner_via_user_dept:
            # 子查询：manager_id IN (用户.department_id = user_dept_id)
            from app.modules.auth.models import User
            sub = select(User.id).where(User.department_id == user_dept_id, User.is_active == True)
            return query.where(owner_field.in_(sub))
        return query  # 无可用字段，跳过

    if scope == DATA_SCOPE_DEPT_SUB:
        # 当前部门 + 子部门（异步 helper 处理）
        # 简单同步版本：调用方传 cache 后的 ids
        if direct_dept_field is not None:
            # 同步阻塞调用？需在 service 层 await
            # 这里我们改方案：service 层先调 get_dept_subtree_ids 再传 list
            raise RuntimeError("dept_sub 范围需 service 层先调 get_dept_subtree_ids 并传 ids")
        return query

    if scope == DATA_SCOPE_SELF:
        # 仅自己创建
        if owner_field is not None:
            return query.where(owner_field == current_user.id)
        return query  # 无 owner 字段，跳过

    return query


async def build_data_scope_filter_async(
    db: AsyncSession,
    query,
    model,
    current_user: CurrentUser,
    *,
    owner_field: Optional[InstrumentedAttribute] = None,
    direct_dept_field: Optional[InstrumentedAttribute] = None,
    owner_via_user_dept: bool = False,
):
    """
    async 版本：内部 await get_dept_subtree_ids（用于 dept_sub 范围）
    """
    if current_user.is_admin or current_user.data_scope == DATA_SCOPE_ALL:
        return query

    scope = current_user.data_scope
    user_dept_id = current_user.department_id

    if scope in (DATA_SCOPE_DEPT, DATA_SCOPE_CUSTOM):
        if direct_dept_field is not None:
            return query.where(direct_dept_field == user_dept_id)
        if owner_field is not None and owner_via_user_dept:
            from app.modules.auth.models import User
            sub = select(User.id).where(User.department_id == user_dept_id, User.is_active == True)
            return query.where(owner_field.in_(sub))
        return query

    if scope == DATA_SCOPE_DEPT_SUB:
        if direct_dept_field is not None:
            ids = await get_dept_subtree_ids(db, user_dept_id)
            return query.where(direct_dept_field.in_(ids))
        if owner_field is not None and owner_via_user_dept:
            ids = await get_dept_subtree_ids(db, user_dept_id)
            from app.modules.auth.models import User
            sub = select(User.id).where(User.department_id.in_(ids), User.is_active == True)
            return query.where(owner_field.in_(sub))
        return query

    if scope == DATA_SCOPE_SELF:
        if owner_field is not None:
            return query.where(owner_field == current_user.id)
        return query

    return query
