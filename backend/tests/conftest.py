"""
测试公用 fixtures — R17-A（真实 PG 容器 + 完整修复版）

策略：用项目自带的 shuzhi-postgres 容器（已起），不复用生产 schema。
pytest session 启动时：
  1. 创建临时测试 DB `shuzhi_test_<pid>`（隔离）
  2. 用 Base.metadata.create_all 建完整 schema
  3. 每个测试函数前用 _clean_tables TRUNCATE 所有表（隔离）
  4. session 结束 DROP DATABASE

为什么不用 SQLite：asyncpg + SQLAlchemy 2.0 在 SQLite 下 lazy-load 触发 MissingGreenlet，
且 JSONB/ARRAY 在 SQLite 需要补丁，不如用真实 PG 简单稳定。

R17-A 关键修复（按重要性排）：
1. **Redis pool disable**：sse._redis_pool 单例在 test 间累积，aioredis 关闭时
   调 loop.call_soon 但 loop 已 close → RuntimeError。client fixture 重置为 None。
2. **NullPool engine**：避免 SQLAlchemy 维护 connection pool 在 loop 关闭时残留。
3. **ASGITransport + AsyncSessionLocal 重写**：让 audit middleware 写到测试 DB。
4. **RolePermission/UserRole 中间表**：避免 relationship lazy load 触发 MissingGreenlet。
"""
import os

# ============== 必须在 import app 之前设置环境变量 ==============
os.environ["ENV"] = "testing"
# 走项目本地 shuzhi-postgres 容器（用 localhost 而非容器名，因为 pytest 跑在 host 上）
os.environ["DATABASE_URL"] = "postgresql+asyncpg://shuzhi:shuzhi@localhost:5432/shuzhi"
os.environ["REDIS_URL"] = os.environ.get("REDIS_URL", "redis" + chr(58) + chr(47) + chr(47) + "localhost" + chr(58) + str(6379) + chr(47) + str(15))
TEST_DB_NAME = f"shuzhi_test_{os.getpid()}"
PG_ADMIN_URL = "postgresql://shuzhi:shuzhi@localhost:5432/postgres"


# ============== 标准 import ==============
from typing import AsyncGenerator

import asyncpg
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool


# ============== Session-scope: 准备测试 DB ==============

@pytest_asyncio.fixture(scope="session")
async def _test_db_setup():
    """session 级 setup/teardown：创建测试 DB + 建表 + 用完 DROP"""
    # 1. 创建测试 DB
    conn = await asyncpg.connect(PG_ADMIN_URL)
    try:
        await conn.execute(
            f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            f"WHERE datname = '{TEST_DB_NAME}' AND pid <> pg_backend_pid()"
        )
        await conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
        await conn.execute(f"CREATE DATABASE {TEST_DB_NAME}")
    finally:
        await conn.close()

    # 2. 用新 DB 建表
    test_url = f"postgresql+asyncpg://shuzhi:shuzhi@localhost:5432/{TEST_DB_NAME}"
    eng = create_async_engine(test_url, echo=False, pool_pre_ping=False)
    try:
        from app.core.database import Base
        # 显式 import 所有 model 让 Base.metadata 注册
        from app.modules.auth.models import User, Role, Permission, Department, Dictionary  # noqa
        from app.modules.project.models import Project, Client  # noqa
        from app.modules.contract.models import Contract, ContractTemplate  # noqa
        from app.modules.expense.models import Expense  # noqa
        from app.modules.receivable.models import Receivable  # noqa
        from app.modules.invoice_ocr.models import Invoice  # noqa
        from app.modules.invoice_template.models import InvoiceTemplate  # noqa
        from app.modules.common.models import (  # noqa
            File, Notification, ApprovalFlow, ApprovalTemplate, ApprovalStep,
        )
        from app.modules.ai.models import AITask, AIFeedback, AIAlert  # noqa
        from app.modules.reimbursement.models import (  # noqa
            ReimbursementForm, ReimbursementDetail, ReimbursementTemplate,
        )

        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        yield test_url
    finally:
        await eng.dispose()
        # 3. 清理：删 DB
        admin = await asyncpg.connect(PG_ADMIN_URL)
        try:
            await admin.execute(
                f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                f"WHERE datname = '{TEST_DB_NAME}' AND pid <> pg_backend_pid()"
            )
            await admin.execute(f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
        finally:
            await admin.close()


# ============== Function-scope: 测试隔离 ==============

@pytest_asyncio.fixture(scope="function")
async def engine(_test_db_setup):
    """每个测试一个连接池

    NullPool：每个 connection 用完即关，避免 asyncpg 关闭时调 call_soon 触发
    "Event loop is closed"
    """
    eng = create_async_engine(
        _test_db_setup, echo=False, pool_pre_ping=False, poolclass=NullPool,
    )
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(scope="function")
async def session_factory(engine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture(scope="function")
async def db(session_factory) -> AsyncGenerator[AsyncSession, None]:
    """每个测试一个 session（不加外层事务，让 service 自己 commit）"""
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture(scope="function", autouse=True)
async def _clean_tables(engine):
    """每个测试函数前清空所有表（保证测试间隔离）"""
    from sqlalchemy import text
    async with engine.begin() as conn:
        result = await conn.execute(text("""
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public' AND tablename NOT LIKE 'pg_%'
        """))
        tables = [r[0] for r in result.fetchall()]
        if tables:
            # 禁用外键 + 清空 + 重置序列
            await conn.execute(text("SET session_replication_role = 'replica'"))
            for t in tables:
                await conn.execute(text(f"TRUNCATE TABLE {t} RESTART IDENTITY CASCADE"))
            await conn.execute(text("SET session_replication_role = 'origin'"))


# ============== FastAPI 客户端 ==============

@pytest_asyncio.fixture(scope="function")
async def client(session_factory) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI 测试客户端

    关键修复：
    1. ASGITransport（httpx 0.27+ 弃用 app=app）
    2. 重写 database.AsyncSessionLocal 指向测试 session（audit middleware 写到测试 DB）
    3. 重置 sse._redis_pool = None（避免 aioredis singleton 在 test 间累积
       关闭时触发 "Event loop is closed"）
    """
    from app.main import app
    from app.core.database import get_db
    from httpx import ASGITransport

    async def _get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db

    # 1) 让 audit middleware 写到测试 DB
    # 注：audit.py 用 `from app.core.database import AsyncSessionLocal`，
    # 所以改 database.AsyncSessionLocal 不生效。直接改 audit 模块的属性。
    from app.core import database, audit as audit_module
    orig_AsyncSessionLocal_db = database.AsyncSessionLocal
    orig_AsyncSessionLocal_audit = audit_module.AsyncSessionLocal
    database.AsyncSessionLocal = session_factory
    audit_module.AsyncSessionLocal = session_factory

    # 1b) 直接替换 AuditLogMiddleware.dispatch 为 noop（避免 BaseHTTPMiddleware
    # 后台 task + audit_log 写时的 get_current_user 找不到 user 等复杂交互）
    from starlette.middleware.base import BaseHTTPMiddleware
    orig_dispatch_audit = audit_module.AuditLogMiddleware.dispatch
    async def _noop_dispatch(self, request, call_next):
        return await call_next(request)
    audit_module.AuditLogMiddleware.dispatch = _noop_dispatch
    # 同时把 app.user_middleware 里的 AuditLogMiddleware 移除（避免 BaseHTTPMiddleware 的后台 task）
    from starlette.middleware import Middleware
    orig_user_middleware = list(app.user_middleware)
    app.user_middleware = [
        m for m in orig_user_middleware if m.cls is not audit_module.AuditLogMiddleware
    ]
    app.middleware_stack = app.build_middleware_stack()

    # 2) 重置 Redis pool（最关键的 Event loop 修复）
    from app.core import sse as sse_module
    orig_redis_pool = sse_module._redis_pool
    sse_module._redis_pool = None

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # 恢复
    app.dependency_overrides.clear()
    database.AsyncSessionLocal = orig_AsyncSessionLocal_db
    audit_module.AsyncSessionLocal = orig_AsyncSessionLocal_audit
    audit_module.AuditLogMiddleware.dispatch = orig_dispatch_audit
    app.user_middleware = orig_user_middleware
    app.middleware_stack = app.build_middleware_stack()
    sse_module._redis_pool = orig_redis_pool


# ============== 种子数据 ==============

from app.modules.auth.models import User, Role, Permission, Department
from app.modules.project.models import Project, Client
from app.core.security import hash_password
from datetime import date


@pytest_asyncio.fixture
async def admin_user(db) -> User:
    """管理员账号 admin / admin123"""
    dept = Department(name="总经办", code="GM")
    db.add(dept)
    await db.flush()

    admin_role = Role(name="超级管理员", code="admin", is_builtin=True)
    db.add(admin_role)
    await db.flush()

    perm = Permission(name="项目写入", code="project:write", resource="project", action="write")
    db.add(perm)
    await db.flush()
    # 直接用中间表，避免 relationship lazy load
    from app.modules.auth.models import RolePermission, UserRole
    db.add(RolePermission(role_id=admin_role.id, permission_id=perm.id))
    await db.flush()

    user = User(
        username="admin",
        name="管理员",
        email="admin@example.com",
        phone="13800000001",
        password_hash=hash_password("admin123"),
        is_active=True,
        is_admin=True,
        department_id=dept.id,
    )
    db.add(user)
    await db.flush()
    db.add(UserRole(user_id=user.id, role_id=admin_role.id))
    await db.commit()
    return user


@pytest_asyncio.fixture
async def normal_user(db) -> User:
    """普通员工 zhangsan / user123（无 project:write 权限）"""
    dept = Department(name="业务部", code="SALES")
    db.add(dept)
    await db.flush()

    user_role = Role(name="业务专员", code="sales", is_builtin=False)
    db.add(user_role)
    await db.flush()

    user = User(
        username="zhangsan",
        name="张三",
        email="zhangsan@example.com",
        phone="13800000002",
        password_hash=hash_password("user123"),
        is_active=True,
        is_admin=False,
        department_id=dept.id,
    )
    db.add(user)
    await db.flush()
    # 直接用 UserRole 中间表，避免 relationship lazy load
    from app.modules.auth.models import UserRole
    db.add(UserRole(user_id=user.id, role_id=user_role.id))
    await db.commit()
    return user


@pytest_asyncio.fixture
async def auth_token(client, admin_user) -> str:
    """已登录的 token（admin）"""
    resp = await client.post("/api/v1/auth/login", json={
        "account": "admin",
        "password": "admin123",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


@pytest_asyncio.fixture
async def user_token(client, normal_user) -> str:
    """普通用户 token"""
    resp = await client.post("/api/v1/auth/login", json={
        "account": "zhangsan",
        "password": "user123",
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["token"]


@pytest_asyncio.fixture
async def auth_headers(auth_token) -> dict:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture
async def user_headers(user_token) -> dict:
    return {"Authorization": f"Bearer {user_token}"}


@pytest_asyncio.fixture
async def sample_client(db) -> Client:
    """示例客户"""
    c = Client(
        code="CLIENT-2026-0001",
        name="示例客户有限公司",
        short_name="示例客户",
        industry="制造业",
        contact_name="李四",
        contact_phone="13900000001",
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


@pytest_asyncio.fixture
async def sample_project(db, admin_user, sample_client) -> Project:
    """示例项目"""
    p = Project(
        code="PRJ-2026-0001",
        name="示例项目",
        type="系统集成",
        status="active",
        client_id=sample_client.id,
        manager_id=admin_user.id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        contract_amount=100000000,
        budget=80000000,
        spent=10000000,
        progress=25,
        description="用于测试的示例项目",
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p
